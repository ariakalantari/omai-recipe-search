import pytest
from httpx import ASGITransport, AsyncClient

from recipe_search.config import Settings
from recipe_search.main import create_app
from recipe_search.service import SearchService


@pytest.mark.asyncio
async def test_search_api_and_health(
    search_service: SearchService, test_settings: Settings
) -> None:
    app = create_app(test_settings, service=search_service)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        health = await client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["recipes"] == 12

        landing = await client.get("/")
        assert landing.status_code == 200
        assert "API docs" in landing.text
        assert "Multilingual hybrid search" not in landing.text
        assert 'id="recipe-dialog"' in landing.text

        response = await client.post(
            "/api/search",
            json={"query": "pasta con tomate y ajo", "limit": 3, "ai": "off"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["results"][0]["name"] == "Spanish Garlic Tomato Pasta"
        assert "description" in body["results"][0]
        assert body["results"][0]["instructions"].startswith("Cook the spaghetti")
        assert body["results"][0]["match_reason"]["scores"].keys() == {
            "final",
            "semantic",
            "lexical",
            "ingredient",
        }


@pytest.mark.asyncio
async def test_api_validates_input_contract(
    search_service: SearchService, test_settings: Settings
) -> None:
    app = create_app(test_settings, service=search_service)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.post("/api/search", json={})).status_code == 422
        assert (
            await client.post(
                "/api/search",
                json={"query": "pasta", "ingredients": ["tomato"]},
            )
        ).status_code == 422
        assert (
            await client.post("/api/search", json={"query": "x", "limit": 500})
        ).status_code == 422
