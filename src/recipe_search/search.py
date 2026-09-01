from __future__ import annotations

import hashlib
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import cast

import joblib
import numpy as np
import numpy.typing as npt
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from recipe_search.config import Settings
from recipe_search.domain import (
    InterpretedQuery,
    QueryKind,
    RankedRecipe,
    Recipe,
    ScoreBreakdown,
    SearchMode,
)
from recipe_search.embeddings import EmbeddingBackend
from recipe_search.normalization import ingredient_terms, normalize_text, query_ingredients

logger = logging.getLogger(__name__)
FloatVector = npt.NDArray[np.float32]


class SearchIndex:
    """Owns all local retrieval indexes and the explainable hybrid ranker."""

    def __init__(
        self,
        recipes: list[Recipe],
        settings: Settings,
        fingerprint: str,
        embedding_backend: EmbeddingBackend | None,
    ) -> None:
        self.recipes = recipes
        self.settings = settings
        self.fingerprint = fingerprint
        self.embedding_backend = embedding_backend
        self.semantic_warning: str | None = None

        self._ingredient_sets: list[frozenset[str]] = []
        self._ingredient_sizes = np.empty(0, dtype=np.float32)
        self._ingredient_postings: dict[str, npt.NDArray[np.int32]] = {}
        self._lexical_vectorizer: TfidfVectorizer | None = None
        self._lexical_matrix: csr_matrix | None = None
        self._semantic_matrix: npt.NDArray[np.float32] | None = None

    @property
    def semantic_available(self) -> bool:
        return self.embedding_backend is not None and self._semantic_matrix is not None

    @property
    def cache_path(self) -> Path:
        model_name = self.embedding_backend.name if self.embedding_backend else "no-semantic"
        model_hash = hashlib.sha256(model_name.encode()).hexdigest()[:10]
        return self.settings.index_cache_dir / f"{self.fingerprint}-{model_hash}"

    def build(self) -> None:
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self._build_ingredient_index()
        self._load_or_build_lexical_index()
        self._load_or_build_semantic_index()

    def _document_text(self, recipe: Recipe) -> str:
        # Raw quantities add noise to lexical matching and bloat the sparse index.
        return normalize_text(f"{recipe.name} {' '.join(recipe.ingredients)}")[:1600]

    def _build_ingredient_index(self) -> None:
        postings: dict[str, list[int]] = defaultdict(list)
        for index, recipe in enumerate(self.recipes):
            terms: set[str] = set()
            for line in recipe.ingredients:
                terms.update(sys.intern(term) for term in ingredient_terms(line))
            frozen = frozenset(terms)
            self._ingredient_sets.append(frozen)
            for term in frozen:
                postings[term].append(index)
        self._ingredient_postings = {
            term: np.asarray(indices, dtype=np.int32) for term, indices in postings.items()
        }
        self._ingredient_sizes = np.asarray(
            [max(1, len(terms)) for terms in self._ingredient_sets], dtype=np.float32
        )

    def _load_or_build_lexical_index(self) -> None:
        cache_file = self.cache_path / "lexical.joblib"
        try:
            vectorizer, matrix = joblib.load(cache_file)
            if matrix.shape[0] != len(self.recipes):
                raise ValueError("row count does not match dataset")
            self._lexical_vectorizer = vectorizer
            self._lexical_matrix = matrix
            return
        except (OSError, EOFError, ValueError, TypeError):
            cache_file.unlink(missing_ok=True)

        documents = [self._document_text(recipe) for recipe in self.recipes]
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 4),
            min_df=1 if len(documents) < 25 else 2,
            max_features=self.settings.lexical_max_features,
            sublinear_tf=True,
            dtype=np.float32,
        )
        matrix = vectorizer.fit_transform(documents).tocsr()
        joblib.dump((vectorizer, matrix), cache_file, compress=3)
        self._lexical_vectorizer = vectorizer
        self._lexical_matrix = matrix

    def _load_or_build_semantic_index(self) -> None:
        if self.embedding_backend is None:
            return
        cache_file = self.cache_path / "semantic.npy"
        try:
            matrix = np.load(cache_file, allow_pickle=False, mmap_mode="r")
            if matrix.shape[0] != len(self.recipes) or matrix.ndim != 2:
                raise ValueError("shape does not match dataset")
            if matrix.dtype != np.float32:
                raise ValueError("embedding cache has an unexpected dtype")
            if not np.isfinite(matrix).all():
                raise ValueError("embedding cache contains non-finite values")
            self._semantic_matrix = matrix
            return
        except (OSError, ValueError):
            cache_file.unlink(missing_ok=True)

        try:
            temporary = cache_file.with_suffix(".tmp.npy")
            chunk_size = self.settings.embedding_index_chunk_size
            first_end = min(chunk_size, len(self.recipes))
            first_batch = self.embedding_backend.encode(
                recipe.search_text[:2000] for recipe in self.recipes[:first_end]
            )
            if first_batch.ndim != 2 or first_batch.shape[0] != first_end:
                raise ValueError("embedding backend returned an unexpected shape")
            matrix = np.lib.format.open_memmap(
                temporary,
                mode="w+",
                dtype=np.float32,
                shape=(len(self.recipes), first_batch.shape[1]),
            )
            matrix[:first_end] = first_batch
            for start in range(first_end, len(self.recipes), chunk_size):
                end = min(start + chunk_size, len(self.recipes))
                batch = self.embedding_backend.encode(
                    recipe.search_text[:2000] for recipe in self.recipes[start:end]
                )
                if batch.shape != (end - start, matrix.shape[1]):
                    raise ValueError("embedding backend returned an unexpected shape")
                matrix[start:end] = batch
            matrix.flush()
            del matrix
            temporary.replace(cache_file)
            self._semantic_matrix = np.load(cache_file, allow_pickle=False, mmap_mode="r")
        except Exception as exc:
            cache_file.with_suffix(".tmp.npy").unlink(missing_ok=True)
            self.semantic_warning = f"Semantic index unavailable: {type(exc).__name__}"
            logger.warning(self.semantic_warning)
            self.embedding_backend = None
            self._semantic_matrix = None

    def _lexical_scores(self, query: str) -> FloatVector:
        assert self._lexical_vectorizer is not None
        assert self._lexical_matrix is not None
        query_vector = self._lexical_vectorizer.transform([normalize_text(query)])
        scores = np.asarray((self._lexical_matrix @ query_vector.T).toarray().ravel())
        clipped = np.clip(scores, 0.0, 1.0).astype(np.float32, copy=False)
        return cast(FloatVector, clipped)

    def _semantic_scores(self, query: str) -> FloatVector | None:
        if not self.semantic_available:
            return None
        assert self.embedding_backend is not None
        assert self._semantic_matrix is not None
        query_vector = self.embedding_backend.encode([query])[0]
        scores = self._semantic_matrix @ query_vector
        clipped = np.clip(scores, 0.0, 1.0).astype(np.float32, copy=False)
        return cast(FloatVector, clipped)

    def _ingredient_scores(self, query_terms: tuple[str, ...]) -> FloatVector:
        scores = np.zeros(len(self.recipes), dtype=np.float32)
        if not query_terms:
            return scores
        counts = np.zeros(len(self.recipes), dtype=np.float32)
        for term in query_terms:
            indices = self._ingredient_postings.get(term)
            if indices is not None:
                counts[indices] += 1.0
        coverage = counts / len(query_terms)
        cosine = counts / np.sqrt(len(query_terms) * self._ingredient_sizes)
        return np.clip(0.8 * coverage + 0.2 * cosine, 0.0, 1.0)

    def _weights(
        self, kind: QueryKind, semantic_scores: FloatVector | None
    ) -> tuple[float, float, float]:
        semantic, lexical, ingredient = (
            (0.30, 0.15, 0.55) if kind is QueryKind.INGREDIENTS else (0.55, 0.25, 0.20)
        )
        if semantic_scores is None:
            available = lexical + ingredient
            return 0.0, lexical / available, ingredient / available
        return semantic, lexical, ingredient

    def search(
        self,
        interpreted: InterpretedQuery,
        *,
        limit: int,
        mode: SearchMode,
    ) -> list[RankedRecipe]:
        lexical = self._lexical_scores(interpreted.original)
        semantic = self._semantic_scores(interpreted.semantic_text)
        ingredient_query = interpreted.ingredients or query_ingredients([interpreted.original])
        ingredient = self._ingredient_scores(ingredient_query)

        if mode is SearchMode.LEXICAL:
            final = lexical.copy()
        elif mode is SearchMode.SEMANTIC:
            final = semantic.copy() if semantic is not None else lexical.copy()
        else:
            semantic_weight, lexical_weight, ingredient_weight = self._weights(
                interpreted.kind, semantic
            )
            final = lexical_weight * lexical + ingredient_weight * ingredient
            if semantic is not None:
                final += semantic_weight * semantic

        excluded_terms = query_ingredients(interpreted.excluded_ingredients)
        if excluded_terms:
            for index, terms in enumerate(self._ingredient_sets):
                if terms.intersection(excluded_terms):
                    final[index] *= 0.15

        top_indices = np.argsort(-final, kind="stable")[:limit]
        results: list[RankedRecipe] = []
        query_term_set = set(ingredient_query)
        for index in top_indices:
            matched = tuple(sorted(query_term_set.intersection(self._ingredient_sets[index])))
            results.append(
                RankedRecipe(
                    recipe=self.recipes[index],
                    scores=ScoreBreakdown(
                        final=float(final[index]),
                        semantic=None if semantic is None else float(semantic[index]),
                        lexical=float(lexical[index]),
                        ingredient=float(ingredient[index]),
                        matched_ingredients=matched,
                    ),
                )
            )
        return results
