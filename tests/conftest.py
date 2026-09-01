from __future__ import annotations

from pathlib import Path

import pytest

from recipe_search.config import Settings
from recipe_search.embeddings import HashEmbeddingBackend
from recipe_search.service import SearchService, build_search_service


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        recipe_data_path=Path("data/sample_recipes.json"),
        index_cache_dir=tmp_path / "cache",
        embedding_cache_dir=tmp_path / "models",
        azure_openai_base_url=None,
        azure_openai_api_key=None,
    )


@pytest.fixture
def search_service(test_settings: Settings) -> SearchService:
    return build_search_service(test_settings, embedding_backend=HashEmbeddingBackend())
