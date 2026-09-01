from __future__ import annotations

import pytest

from recipe_search.domain import SearchMode
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
