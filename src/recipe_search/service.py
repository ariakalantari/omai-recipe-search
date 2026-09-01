from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Literal

from recipe_search.config import Settings
from recipe_search.domain import LoadReport
from recipe_search.embeddings import EmbeddingBackend, FastEmbedBackend
from recipe_search.loader import load_recipes
from recipe_search.query_understanding import (
    AzureOpenAIQueryInterpreter,
    HeuristicQueryInterpreter,
)
from recipe_search.schemas import (
    QueryUnderstandingResponse,
    RecipeResponse,
    SearchMetaResponse,
    SearchRequest,
    SearchResponse,
)
from recipe_search.search import SearchIndex

logger = logging.getLogger(__name__)


class MinuteRateLimiter:
    """Small demo safeguard for costly AI calls; not a distributed quota system."""

    def __init__(self, global_limit: int, client_limit: int) -> None:
        self._global_limit = global_limit
        self._client_limit = client_limit
        self._global: deque[float] = deque()
        self._clients: defaultdict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _prune(events: deque[float], now: float) -> None:
        while events and events[0] <= now - 60:
            events.popleft()

    def allow(self, client_id: str) -> bool:
        if self._global_limit == 0 or self._client_limit == 0:
            return False
        now = time.monotonic()
        client_events = self._clients[client_id]
        self._prune(self._global, now)
        self._prune(client_events, now)
        if len(self._global) >= self._global_limit or len(client_events) >= self._client_limit:
            return False
        self._global.append(now)
        client_events.append(now)
        return True


@dataclass(slots=True)
class SearchService:
    settings: Settings
    index: SearchIndex
    load_report: LoadReport
    heuristic: HeuristicQueryInterpreter
    azure: AzureOpenAIQueryInterpreter
    ai_limiter: MinuteRateLimiter

    @property
    def ai_available(self) -> bool:
        return self.azure.available

    async def search(self, request: SearchRequest, client_id: str = "unknown") -> SearchResponse:
        if request.ingredients is not None:
            interpreted = self.heuristic.from_ingredients(request.ingredients)
        elif request.ai == "auto" and self.azure.available:
            if self.ai_limiter.allow(client_id):
                interpreted = await self.azure.interpret(request.query or "")
            else:
                fallback = await self.heuristic.interpret(request.query or "")
                interpreted = type(fallback)(
                    original=fallback.original,
                    kind=fallback.kind,
                    ingredients=fallback.ingredients,
                    excluded_ingredients=fallback.excluded_ingredients,
                    preferences=fallback.preferences,
                    max_minutes=fallback.max_minutes,
                    source=fallback.source,
                    degraded=True,
                    warning="AI rate limit reached; deterministic fallback used.",
                )
        else:
            interpreted = await self.heuristic.interpret(request.query or "")

        ranked = await asyncio.to_thread(
            self.index.search,
            interpreted,
            limit=request.limit,
            mode=request.mode,
        )
        top_score = ranked[0].scores.final if ranked else 0.0
        confidence: Literal["high", "medium", "low"] = "low"
        if top_score >= 0.55:
            confidence = "high"
        elif top_score >= self.settings.low_confidence_threshold:
            confidence = "medium"
        query_text = request.query or ", ".join(request.ingredients or [])
        return SearchResponse(
            query=query_text,
            results=[RecipeResponse.from_ranked(item) for item in ranked],
            meta=SearchMetaResponse(
                mode=request.mode,
                total_recipes=len(self.index.recipes),
                returned=len(ranked),
                confidence=confidence,
                semantic_available=self.index.semantic_available,
                ai_available=self.ai_available,
                query_understanding=QueryUnderstandingResponse.from_domain(interpreted),
            ),
        )


def build_search_service(
    settings: Settings,
    *,
    embedding_backend: EmbeddingBackend | None = None,
) -> SearchService:
    recipes, report, fingerprint = load_recipes(
        settings.recipe_data_path, max_recipes=settings.max_recipes
    )
    # A slice of a dataset is a different index artifact even when source bytes are identical.
    fingerprint = f"{fingerprint}-{len(recipes)}"
    backend = embedding_backend
    if settings.semantic_enabled and backend is None:
        try:
            backend = FastEmbedBackend(
                settings.embedding_model,
                str(settings.embedding_cache_dir),
                settings.embedding_batch_size,
                settings.embedding_parallel_workers,
            )
        except Exception as exc:
            warning = f"Semantic model unavailable: {type(exc).__name__}"
            logger.warning(warning)
            report.warnings.append(warning)
    index = SearchIndex(recipes, settings, fingerprint, backend)
    index.build()
    if index.semantic_warning:
        report.warnings.append(index.semantic_warning)
    heuristic = HeuristicQueryInterpreter()
    azure = AzureOpenAIQueryInterpreter(settings, heuristic)
    return SearchService(
        settings=settings,
        index=index,
        load_report=report,
        heuristic=heuristic,
        azure=azure,
        ai_limiter=MinuteRateLimiter(
            settings.ai_requests_per_minute,
            settings.ai_requests_per_client_minute,
        ),
    )
