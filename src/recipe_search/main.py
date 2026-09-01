from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from recipe_search.config import Settings, get_settings
from recipe_search.schemas import HealthResponse, SearchRequest, SearchResponse
from recipe_search.service import SearchService, build_search_service


def create_app(
    settings: Settings | None = None,
    *,
    service: SearchService | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if service is not None:
            app.state.search_service = service
        else:
            app.state.search_service = await asyncio.to_thread(
                build_search_service, runtime_settings
            )
        yield

    logging.basicConfig(
        level=getattr(logging, runtime_settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = FastAPI(
        title=runtime_settings.app_name,
        version="0.1.0",
        description=(
            "Explainable multilingual recipe retrieval using deterministic ingredient matching, "
            "lexical TF-IDF, and local semantic embeddings."
        ),
        lifespan=lifespan,
    )

    @app.get("/healthz", response_model=HealthResponse, tags=["operations"])
    async def health(request: Request) -> HealthResponse:
        current: SearchService = request.app.state.search_service
        degraded = not current.index.semantic_available or bool(current.load_report.warnings)
        return HealthResponse(
            status="degraded" if degraded else "ok",
            recipes=len(current.index.recipes),
            semantic_available=current.index.semantic_available,
            ai_available=current.ai_available,
            load_warnings=current.load_report.warnings,
        )

    @app.get("/readyz", include_in_schema=False)
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/api/search", response_model=SearchResponse, tags=["search"])
    async def search(payload: SearchRequest, request: Request) -> SearchResponse:
        current: SearchService = request.app.state.search_service
        client_id = request.client.host if request.client else "unknown"
        return await current.search(payload, client_id=client_id)

    @app.get("/api", include_in_schema=False)
    async def api_root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    static_dir = Path(__file__).with_name("static")
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app


app = create_app()
