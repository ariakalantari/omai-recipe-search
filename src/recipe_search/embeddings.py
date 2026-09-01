from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, cast

import numpy as np
import numpy.typing as npt

FloatMatrix = npt.NDArray[np.float32]


class EmbeddingBackend(Protocol):
    name: str

    def encode(self, texts: Iterable[str]) -> FloatMatrix: ...


def l2_normalize(values: FloatMatrix) -> FloatMatrix:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    normalized = (values / np.maximum(norms, 1e-12)).astype(np.float32, copy=False)
    return cast(FloatMatrix, normalized)


class FastEmbedBackend:
    """Small ONNX-backed multilingual embedding adapter."""

    def __init__(
        self,
        model_name: str,
        cache_dir: str,
        batch_size: int = 256,
        parallel_workers: int = 4,
    ) -> None:
        from fastembed import TextEmbedding

        self.name = model_name
        self._batch_size = batch_size
        self._parallel_workers = parallel_workers
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def encode(self, texts: Iterable[str]) -> FloatMatrix:
        documents = list(texts)
        # FastEmbed's process pool is unnecessary with one worker and can fail in constrained
        # ARM containers. Treat a value of 1 as an explicit single-process mode.
        parallel = (
            self._parallel_workers
            if self._parallel_workers > 1 and len(documents) >= self._batch_size * 4
            else None
        )
        vectors = list(self._model.embed(documents, batch_size=self._batch_size, parallel=parallel))
        if not vectors:
            return np.empty((0, 0), dtype=np.float32)
        return l2_normalize(np.asarray(vectors, dtype=np.float32))


class HashEmbeddingBackend:
    """Deterministic lightweight backend used by tests, never production."""

    name = "test/hash-embedding"

    def __init__(self, dimensions: int = 64) -> None:
        self._dimensions = dimensions

    def encode(self, texts: Iterable[str]) -> FloatMatrix:
        from recipe_search.normalization import normalize_text

        rows: list[npt.NDArray[np.float32]] = []
        for text in texts:
            vector = np.zeros(self._dimensions, dtype=np.float32)
            normalized = normalize_text(text)
            grams = [normalized[index : index + 3] for index in range(max(1, len(normalized) - 2))]
            for gram in grams:
                vector[hash(gram) % self._dimensions] += 1.0
            rows.append(vector)
        if not rows:
            return np.empty((0, self._dimensions), dtype=np.float32)
        return l2_normalize(np.stack(rows))
