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
        assert "How it works" in landing.text
        assert 'id="how-dialog"' in landing.text
        assert 'class="food-icons"' in landing.text
        assert "Multilingual hybrid search" not in landing.text
        assert 'id="recipe-dialog"' in landing.text

        script = await client.get("/app.js")
        assert script.status_code == 200
        assert "renderPage({ animate: true })" in script.text
        assert "renderPage({ scroll: true })" in script.text
        assert "skeleton" not in script.text
        assert 'classList.add("modal-open")' in script.text
        assert 'addEventListener("close", releaseDialogScroll)' in script.text
        assert "--locked-scroll-offset" in script.text

        stylesheet = await client.get("/styles.css")
        assert stylesheet.status_code == 200
        assert ".animate-results .recipe-card" in stylesheet.text
        assert "@keyframes card-arrive" in stylesheet.text
        assert "html.modal-open, body.modal-open" in stylesheet.text
        assert "overscroll-behavior: contain" in stylesheet.text
        assert "@keyframes shimmer" not in stylesheet.text

        favicon = await client.get("/favicon.svg")
        assert favicon.status_code == 200
        assert "#d4663d" in favicon.text
        assert "#d88a2d" in favicon.text
        assert "#64915f" in favicon.text

        response = await client.post(
            "/api/search",
            json={"query": "pasta con tomate y ajo", "limit": 3, "ai": "off"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["results"][0]["name"] == "Spanish Garlic Tomato Pasta"
        assert "description" in body["results"][0]
        assert body["results"][0]["summary"].startswith("A pasta dish featuring")
        assert body["results"][0]["instructions"].startswith("Cook the spaghetti")
        assert body["results"][0]["match_reason"]["scores"].keys() == {
            "final",
            "semantic",
            "lexical",
            "ingredient",
            "distinctiveness",
        }
        assert body["meta"]["strategy"] == "search"
        assert response.headers["cache-control"] == "no-store"
        assert landing.headers["x-frame-options"] == "DENY"
        assert "default-src 'self'" in landing.headers["content-security-policy"]


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
        assert (await client.post("/api/search", json={"query": "🍕"})).status_code == 422


@pytest.mark.asyncio
async def test_api_rejects_large_bodies_without_reflecting_them(
    search_service: SearchService, test_settings: Settings
) -> None:
    app = create_app(test_settings, service=search_service)
    oversized = '{"query":"' + ("private-text" * 2000) + '"}'
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post(
            "/api/search",
            content=oversized,
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 413
        assert len(response.content) < 200
        assert "private-text" not in response.text

        invalid = await client.post("/api/search", json={"query": "x" * 501})
        assert invalid.status_code == 422
        assert "x" * 100 not in invalid.text
