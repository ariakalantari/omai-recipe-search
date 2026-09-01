from __future__ import annotations

import pytest

from recipe_search.config import Settings
from recipe_search.query_understanding import (
    AzureOpenAIQueryInterpreter,
    HeuristicQueryInterpreter,
)
from recipe_search.service import MinuteRateLimiter


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
    assert result.ingredients == ("cod", "coconut milk")
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
