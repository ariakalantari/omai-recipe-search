from __future__ import annotations

import hashlib
import logging
import math
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
    QueryIntent,
    QueryKind,
    RankedRecipe,
    Recipe,
    ScoreBreakdown,
    SearchMode,
    SearchOutcome,
    SearchStrategy,
)
from recipe_search.embeddings import EmbeddingBackend
from recipe_search.normalization import (
    distinctive_ingredient_terms,
    ingredient_terms,
    normalize_text,
    query_ingredients,
)

logger = logging.getLogger(__name__)
FloatVector = npt.NDArray[np.float32]
INDEX_SCHEMA_VERSION = "3-balanced-discovery-summaries"
_SPICY_TERMS = {
    "cayenne",
    "chili",
    "chili sauce",
    "hot sauce",
    "jalapeno",
    "pepper flake",
    "sambal",
    "sriracha",
}
_NON_DISH_TITLE_TERMS = {
    "ale",
    "cocktail",
    "drink",
    "frosting",
    "lemonade",
    "margarita",
    "martini",
    "punch",
    "sauce",
    "seasoning",
    "shake",
    "smoothie",
}
_CATEGORY_TERMS = {
    "dessert": {"brownie", "cake", "cookie", "cupcake", "gelato", "ice cream", "pie"},
    "salad": {"salad", "slaw"},
    "soup": {"chili", "stew", "soup"},
    "pasta": {"lasagna", "noodle", "pasta", "spaghetti"},
    "bread": {"bread", "biscuit", "muffin"},
    "seafood": {"cod", "crab", "fish", "salmon", "shrimp", "tuna"},
    "handheld": {"burger", "sandwich", "taco", "tortilla", "wrap"},
}


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
        self._distinctiveness_scores = np.empty(0, dtype=np.float32)
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
        return self.settings.index_cache_dir / (
            f"{INDEX_SCHEMA_VERSION}-{self.fingerprint}-{model_hash}"
        )

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
        distinctive_sets: list[frozenset[str]] = []
        for index, recipe in enumerate(self.recipes):
            terms: set[str] = set()
            distinctive: set[str] = set()
            for line in recipe.ingredients:
                terms.update(sys.intern(term) for term in ingredient_terms(line))
                distinctive.update(distinctive_ingredient_terms(line))
            frozen = frozenset(terms)
            self._ingredient_sets.append(frozen)
            distinctive_sets.append(frozenset(distinctive))
            for term in frozen:
                postings[term].append(index)
        self._ingredient_postings = {
            term: np.asarray(indices, dtype=np.int32) for term, indices in postings.items()
        }
        self._ingredient_sizes = np.asarray(
            [max(1, len(terms)) for terms in self._ingredient_sets], dtype=np.float32
        )
        self._distinctiveness_scores = self._build_distinctiveness_scores(distinctive_sets)

    def _build_distinctiveness_scores(self, term_sets: list[frozenset[str]]) -> FloatVector:
        """Estimate corpus-relative novelty while limiting rare-token noise."""
        document_frequency: dict[str, int] = defaultdict(int)
        for terms in term_sets:
            for term in terms:
                document_frequency[term] += 1

        recipe_count = len(term_sets)
        minimum_frequency = 1 if recipe_count < 50 else 3
        maximum_frequency = max(minimum_frequency, int(recipe_count * 0.15))
        idf_cap = math.log((recipe_count + 1) / (minimum_frequency + 1))
        raw = np.zeros(recipe_count, dtype=np.float32)
        for index, terms in enumerate(term_sets):
            values = sorted(
                (
                    min(
                        idf_cap,
                        math.log((recipe_count + 1) / (document_frequency[term] + 1)),
                    )
                    for term in terms
                    if minimum_frequency <= document_frequency[term] <= maximum_frequency
                ),
                reverse=True,
            )[:6]
            if len(values) >= 2:
                raw[index] = sum(values) / 6

        positive = raw[raw > 0]
        if positive.size < 2:
            return raw
        low = float(np.percentile(positive, 20))
        high = float(np.percentile(positive, 98))
        if high <= low:
            return cast(FloatVector, np.clip(raw, 0.0, 1.0))
        normalized = np.clip((raw - low) / (high - low), 0.0, 1.0).astype(np.float32, copy=False)
        return cast(FloatVector, normalized)

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
        encoded = self.embedding_backend.encode([query])
        if encoded.ndim != 2 or encoded.shape != (1, self._semantic_matrix.shape[1]):
            raise ValueError("embedding backend returned an unexpected query shape")
        if not np.isfinite(encoded).all():
            raise ValueError("embedding backend returned a non-finite query vector")
        query_vector = encoded[0]
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

    def _supported_ingredient_terms(self, terms: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(term for term in terms if term in self._ingredient_postings)

    def _diverse_top_indices(
        self,
        scores: FloatVector,
        *,
        limit: int,
        candidate_count: int = 250,
    ) -> list[int]:
        ordered = [
            int(index)
            for index in np.argsort(-scores, kind="stable")[:candidate_count]
            if np.isfinite(scores[index])
        ]
        selected: list[int] = []
        seen_names: set[str] = set()
        category_counts: dict[str, int] = defaultdict(int)
        while ordered and len(selected) < limit:
            best_index: int | None = None
            best_value = -math.inf
            for index in ordered:
                normalized_name = normalize_text(self.recipes[index].name)
                if normalized_name in seen_names:
                    continue
                name_terms = set(normalized_name.split())
                if name_terms.intersection(_NON_DISH_TITLE_TERMS):
                    continue
                category = self._recipe_category(normalized_name)
                similarity = 0.0
                for chosen in selected:
                    union = self._ingredient_sets[index].union(self._ingredient_sets[chosen])
                    if union:
                        similarity = max(
                            similarity,
                            len(
                                self._ingredient_sets[index].intersection(
                                    self._ingredient_sets[chosen]
                                )
                            )
                            / len(union),
                        )
                category_penalty = 0.1 * min(2, category_counts[category])
                value = float(scores[index]) - 0.18 * similarity - category_penalty
                if value > best_value:
                    best_index = index
                    best_value = value
            if best_index is None:
                break
            selected.append(best_index)
            seen_names.add(normalize_text(self.recipes[best_index].name))
            category_counts[self._recipe_category(self.recipes[best_index].name)] += 1
            ordered.remove(best_index)
        return selected

    @staticmethod
    def _recipe_category(name: str) -> str:
        normalized = normalize_text(name)
        for category, terms in _CATEGORY_TERMS.items():
            if any(term in normalized for term in terms):
                return category
        return "other"

    def _standard_top_indices(self, scores: FloatVector, limit: int) -> list[int]:
        selected: list[int] = []
        seen_names: set[str] = set()
        for raw_index in np.argsort(-scores, kind="stable"):
            index = int(raw_index)
            if not np.isfinite(scores[index]):
                continue
            normalized_name = normalize_text(self.recipes[index].name)
            if normalized_name in seen_names:
                continue
            selected.append(index)
            seen_names.add(normalized_name)
            if len(selected) >= limit:
                break
        return selected

    def search(
        self,
        interpreted: InterpretedQuery,
        *,
        limit: int,
        mode: SearchMode,
    ) -> SearchOutcome:
        lexical = self._lexical_scores(interpreted.original)
        semantic: FloatVector | None = None
        semantic_degraded = False
        semantic_warning: str | None = None
        use_semantic = mode is not SearchMode.LEXICAL and not (
            interpreted.intent in {QueryIntent.ADVENTUROUS, QueryIntent.BROWSE}
            and not interpreted.ingredients
            and not interpreted.preferences
        )
        if use_semantic:
            try:
                semantic = self._semantic_scores(interpreted.semantic_text)
            except Exception as exc:
                semantic_degraded = True
                semantic_warning = "Semantic query processing failed; local lexical fallback used."
                logger.warning("Semantic query failed; using fallback: %s", type(exc).__name__)

        raw_ingredient_query = interpreted.ingredients or query_ingredients([interpreted.original])
        ingredient_query = self._supported_ingredient_terms(raw_ingredient_query)
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

        strategy = SearchStrategy.SEARCH
        has_constraints = bool(ingredient_query or interpreted.preferences)
        if interpreted.intent is QueryIntent.ADVENTUROUS:
            strategy = SearchStrategy.ADVENTUROUS
            final = (
                0.82 * final + 0.18 * self._distinctiveness_scores
                if has_constraints
                else self._distinctiveness_scores.copy()
            )
        elif interpreted.intent is QueryIntent.BROWSE:
            strategy = SearchStrategy.DISCOVERY
            final = self._distinctiveness_scores.copy()
        else:
            supported_ratio = len(ingredient_query) / max(1, len(raw_ingredient_query))
            ingredient_signal = float(np.max(ingredient, initial=0.0))
            lexical_signal = float(np.max(lexical, initial=0.0))
            semantic_signal = float(np.max(semantic, initial=0.0)) if semantic is not None else 0.0
            semantic_floor = (
                0.45
                if any(
                    character.isalpha() and not character.isascii()
                    for character in interpreted.original
                )
                else 0.6
            )
            low_signal = (
                not interpreted.preferences
                and (supported_ratio < 0.5 or ingredient_signal < 0.3)
                and lexical_signal < 0.3
                and semantic_signal < semantic_floor
            )
        if interpreted.intent is QueryIntent.SEARCH and low_signal:
            strategy = SearchStrategy.DISCOVERY
            final = self._distinctiveness_scores.copy()
            semantic_warning = (
                "We could not identify a specific cooking request, so these are varied ideas "
                "from the collection. Add an ingredient, cuisine, mood, or cooking time for "
                "closer matches."
            )

        excluded_terms = query_ingredients(interpreted.excluded_ingredients)
        if excluded_terms:
            for index, terms in enumerate(self._ingredient_sets):
                if terms.intersection(excluded_terms):
                    final[index] = -np.inf
        if "spicy" in interpreted.excluded_preferences:
            for index, terms in enumerate(self._ingredient_sets):
                if (
                    terms.intersection(_SPICY_TERMS)
                    or "spicy" in normalize_text(self.recipes[index].name).split()
                ):
                    final[index] = -np.inf

        if strategy is SearchStrategy.SEARCH:
            top_indices = self._standard_top_indices(final, limit)
        else:
            top_indices = self._diverse_top_indices(final, limit=limit)
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
                        distinctiveness=float(self._distinctiveness_scores[index]),
                        matched_ingredients=matched,
                    ),
                )
            )
        return SearchOutcome(
            results=tuple(results),
            strategy=strategy,
            semantic_degraded=semantic_degraded,
            warning=semantic_warning,
        )
