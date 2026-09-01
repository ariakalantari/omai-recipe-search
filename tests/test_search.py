from __future__ import annotations

import pytest

from recipe_search.domain import SearchMode, SearchStrategy
from recipe_search.schemas import SearchRequest
from recipe_search.service import SearchService, build_search_service


@pytest.mark.asyncio
async def test_explicit_ingredient_search_is_deterministic(search_service: SearchService) -> None:
    response = await search_service.search(
        SearchRequest(ingredients=["eggs", "potatoes", "onion"], limit=3),
        client_id="test",
    )
    assert response.results[0].name == "Potato, Egg and Onion Tortilla"
    assert response.results[0].match_reason.scores.ingredient > 0.7
    assert response.meta.query_understanding.source == "deterministic"


@pytest.mark.asyncio
async def test_swedish_query_retrieves_cod_and_coconut(search_service: SearchService) -> None:
    response = await search_service.search(
        SearchRequest(query="något starkt med torsk och kokosmjölk", limit=3, ai="off"),
        client_id="test",
    )
    assert response.results[0].name == "Spicy Coconut Cod Curry"
    assert {"cod", "coconut", "milk"}.intersection(
        response.results[0].match_reason.matched_ingredients
    )


@pytest.mark.asyncio
async def test_search_modes_use_same_contract(search_service: SearchService) -> None:
    for mode in SearchMode:
        response = await search_service.search(
            SearchRequest(query="pasta with tomato and garlic", mode=mode, limit=2, ai="off"),
            client_id="test",
        )
        assert response.meta.mode == mode
        assert len(response.results) == 2


@pytest.mark.asyncio
async def test_semantic_failure_degrades_to_lexical(test_settings) -> None:
    settings = test_settings.model_copy(update={"semantic_enabled": False})
    service = build_search_service(settings)
    response = await service.search(
        SearchRequest(query="tomato garlic pasta", mode=SearchMode.SEMANTIC, limit=1, ai="off")
    )
    assert response.meta.semantic_available is False
    assert response.results[0].name == "Spanish Garlic Tomato Pasta"


@pytest.mark.asyncio
async def test_low_signal_text_uses_honest_discovery_fallback(test_settings) -> None:
    settings = test_settings.model_copy(update={"semantic_enabled": False})
    service = build_search_service(settings)
    response = await service.search(SearchRequest(query="xyzzy quantum foam", limit=3, ai="off"))
    assert response.meta.strategy == SearchStrategy.DISCOVERY
    assert response.meta.confidence == "low"
    assert "varied ideas" in (response.meta.retrieval_warning or "")


@pytest.mark.asyncio
async def test_adventurous_query_returns_diverse_grounded_results(
    search_service: SearchService,
) -> None:
    response = await search_service.search(
        SearchRequest(query="something I haven't had before", limit=5, ai="off")
    )
    assert response.meta.strategy == SearchStrategy.ADVENTUROUS
    assert len({result.name for result in response.results}) == 5
    assert all(
        result.summary and not result.summary.startswith("Preheat") for result in response.results
    )


@pytest.mark.asyncio
async def test_excluded_ingredient_is_never_returned(search_service: SearchService) -> None:
    response = await search_service.search(
        SearchRequest(query="chicken without garlic", limit=8, ai="off")
    )
    assert response.meta.query_understanding.excluded_ingredients == ["garlic"]
    assert all(
        "garlic" not in " ".join(result.ingredients).casefold() for result in response.results
    )


@pytest.mark.asyncio
async def test_negated_spicy_preference_is_not_rewarded(search_service: SearchService) -> None:
    response = await search_service.search(
        SearchRequest(query="not spicy chicken", limit=3, ai="off")
    )
    assert response.meta.query_understanding.preferences == []
    assert response.meta.query_understanding.excluded_preferences == ["spicy"]
    assert "spicy" not in response.results[0].name.casefold()


@pytest.mark.asyncio
async def test_query_embedding_failure_degrades_per_request(
    search_service: SearchService, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert search_service.index.embedding_backend is not None

    def fail(_texts: object) -> object:
        raise RuntimeError("provider detail that must stay internal")

    monkeypatch.setattr(search_service.index.embedding_backend, "encode", fail)
    response = await search_service.search(
        SearchRequest(query="tomato garlic pasta", limit=2, ai="off")
    )
    assert response.meta.semantic_degraded is True
    assert response.results
    assert "provider detail" not in (response.meta.retrieval_warning or "")


@pytest.mark.asyncio
async def test_lexical_mode_skips_query_embedding(
    search_service: SearchService, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert search_service.index.embedding_backend is not None

    def fail(_texts: object) -> object:
        raise AssertionError("lexical mode must not call embeddings")

    monkeypatch.setattr(search_service.index.embedding_backend, "encode", fail)
    response = await search_service.search(
        SearchRequest(query="tomato garlic pasta", mode=SearchMode.LEXICAL, limit=2, ai="off")
    )
    assert response.meta.semantic_degraded is False
    assert response.results
