from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from recipe_search.config import Settings, get_settings
from recipe_search.schemas import HealthResponse, SearchRequest, SearchResponse
from recipe_search.service import SearchCapacityError, SearchService, build_search_service

_JSON_CONTENT_TYPE: Final = "application/json"
_OPENAPI_TAGS: Final = [
    {
        "name": "search",
        "description": (
            "Retrieve and rank recipes using ingredient, lexical, and multilingual semantic signals."
        ),
    },
    {
        "name": "operations",
        "description": "Inspect application health and retrieval capability availability.",
    },
]


class RequestTooLargeError(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Reject oversized API bodies before JSON parsing or validation reflection."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not str(scope.get("path", "")).startswith("/api/"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        try:
            content_length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            content_length = 0
        if content_length > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLargeError:
            await self._reject(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={"detail": "Request body is too large."},
        )
        await response(scope, receive, send)


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
            "lexical TF-IDF, and local semantic embeddings. Optional Azure AI only interprets "
            "complex query constraints. The local ranker always selects the recipes."
        ),
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=runtime_settings.max_request_body_bytes,
    )
    if runtime_settings.allowed_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(runtime_settings.allowed_cors_origins),
            allow_credentials=False,
            allow_methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type"],
            max_age=600,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "loc": list(error.get("loc", ())),
                "msg": error.get("msg", "Invalid request."),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.exception_handler(SearchCapacityError)
    async def capacity_error_handler(_request: Request, _exc: SearchCapacityError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Search is busy. Please try again shortly."},
            headers={"Retry-After": "2"},
        )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        path = request.url.path
        if path == "/" or path.endswith((".js", ".css", ".svg")):
            response.headers["Cache-Control"] = "no-cache"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; base-uri 'none'; object-src 'none'; "
                "frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; "
                "style-src 'self'; script-src 'self'; connect-src 'self'"
            )
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get(
        "/healthz",
        response_model=HealthResponse,
        tags=["operations"],
        summary="Inspect search service health",
        description=(
            "Reports recipe coverage and whether semantic retrieval and optional Azure query "
            "interpretation are available. A degraded service can still provide lexical and "
            "ingredient search."
        ),
    )
    async def health(request: Request) -> HealthResponse:
        current: SearchService = request.app.state.search_service
        degraded = not current.index.semantic_available or bool(current.load_report.warnings)
        return HealthResponse(
            status="degraded" if degraded else "ok",
            recipes=len(current.index.recipes),
            semantic_available=current.index.semantic_available,
            ai_available=current.ai_available,
            instruction_coverage=round(
                sum(bool(recipe.instructions) for recipe in current.index.recipes)
                / len(current.index.recipes),
                4,
            ),
            load_warnings=current.load_report.warnings,
        )

    @app.get("/readyz", include_in_schema=False)
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.post(
        "/api/search",
        response_model=SearchResponse,
        tags=["search"],
        summary="Search the recipe collection",
        description=(
            "Submit exactly one natural-language query or ingredient list. Hybrid mode combines "
            "deterministic ingredient coverage, character TF-IDF, and multilingual embeddings. "
            "Scores and interpreted constraints are returned for review."
        ),
        responses={
            413: {"description": "Request body exceeds the configured size limit."},
            503: {"description": "The bounded search worker pool is currently full."},
        },
    )
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
