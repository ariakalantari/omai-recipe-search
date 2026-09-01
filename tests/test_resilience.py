from __future__ import annotations

import asyncio
import threading

import pytest

from recipe_search.config import Settings
from recipe_search.query_understanding import (
    AzureOpenAIQueryInterpreter,
    HeuristicQueryInterpreter,
)
from recipe_search.schemas import SearchRequest
from recipe_search.service import MinuteRateLimiter, SearchCapacityError, SearchService


@pytest.mark.asyncio
async def test_azure_failure_falls_back_without_exposing_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        azure_openai_base_url="https://example.openai.azure.com/openai/v1/",
        azure_openai_api_key="test-only-value",
        azure_openai_deployment="test-deployment",
    )
    interpreter = AzureOpenAIQueryInterpreter(settings, HeuristicQueryInterpreter())

    def fail(_: str) -> None:
        raise TimeoutError("secret provider detail")

    monkeypatch.setattr(interpreter, "_interpret_sync", fail)
    result = await interpreter.interpret("chicken with garlic")
    assert result.degraded is True
    assert result.source == "heuristic"
    assert "secret provider detail" not in (result.warning or "")


@pytest.mark.asyncio
async def test_azure_interpreter_requests_strict_non_stored_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        azure_openai_base_url="https://example.openai.azure.com/openai/v1/",
        azure_openai_api_key="test-only-value",
        azure_openai_deployment="test-deployment",
    )
    interpreter = AzureOpenAIQueryInterpreter(settings, HeuristicQueryInterpreter())
    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs: object) -> object:
            captured.update(kwargs)

            class Response:
                output_text = (
                    '{"ingredients":["cod","coconut milk"],'
                    '"excluded_ingredients":[],"preferences":["spicy"],'
                    '"max_minutes":30}'
                )

            return Response()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(interpreter, "_client", lambda: FakeClient())
    result = await interpreter.interpret("något starkt med torsk och kokosmjölk")
    assert result.source == "azure_openai"
    assert {"cod", "coconut milk"}.issubset(result.ingredients)
    assert captured["store"] is False
    assert captured["reasoning"] == {"effort": "low"}
    text_format = captured["text"]
    assert isinstance(text_format, dict)
    assert text_format["format"]["strict"] is True


def test_ai_rate_limiter_enforces_global_and_per_client_limits() -> None:
    limiter = MinuteRateLimiter(global_limit=2, client_limit=1)
    assert limiter.allow("one") is True
    assert limiter.allow("one") is False
    assert limiter.allow("two") is True
    assert limiter.allow("three") is False


def test_ai_rate_limiter_does_not_retain_denied_client_ids() -> None:
    limiter = MinuteRateLimiter(global_limit=1, client_limit=1)
    assert limiter.allow("allowed") is True
    for index in range(500):
        assert limiter.allow(f"denied-{index}") is False
    assert len(limiter._clients) == 1


def test_simple_queries_do_not_need_optional_ai() -> None:
    assert SearchService._ai_would_help("chicken and rice") is False
    assert (
        SearchService._ai_would_help("dinner without dairy that is ready under 20 minutes") is True
    )


@pytest.mark.asyncio
async def test_ai_rate_limit_fallback_preserves_negative_preferences(
    search_service: SearchService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        type(search_service.azure),
        "available",
        property(lambda _interpreter: True),
    )
    search_service.ai_limiter = MinuteRateLimiter(global_limit=0, client_limit=0)

    response = await search_service.search(
        SearchRequest(query="dinner without spicy food that is ready under 20 minutes")
    )

    assert "spicy" in response.meta.query_understanding.excluded_preferences
    assert response.meta.query_understanding.degraded is True


@pytest.mark.asyncio
async def test_search_rejects_work_when_local_capacity_is_full(
    search_service: SearchService, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = threading.Event()
    release = threading.Event()
    original_search = search_service.index.search
    search_service.search_slots = asyncio.Semaphore(1)

    def blocking_search(*args: object, **kwargs: object) -> object:
        started.set()
        release.wait(timeout=2)
        return original_search(*args, **kwargs)

    monkeypatch.setattr(search_service.index, "search", blocking_search)
    first = asyncio.create_task(search_service.search(SearchRequest(query="chicken", ai="off")))
    assert await asyncio.to_thread(started.wait, 1)
    with pytest.raises(SearchCapacityError):
        await search_service.search(SearchRequest(query="pasta", ai="off"))
    release.set()
    await first
