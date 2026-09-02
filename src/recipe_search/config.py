from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets are read only at runtime."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "OMAI Recipe Search"
    app_env: str = "development"
    log_level: str = "INFO"

    recipe_data_path: Path = Path("data/sample_recipes.json")
    index_cache_dir: Path = Path("data/cache")
    max_recipes: int | None = Field(default=None, ge=1)

    semantic_enabled: bool = True
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_cache_dir: Path = Path("data/models")
    embedding_batch_size: int = Field(default=256, ge=1, le=2048)
    embedding_index_chunk_size: int = Field(default=16_384, ge=128, le=65_536)
    embedding_parallel_workers: int = Field(default=1, ge=1, le=16)
    lexical_max_features: int = Field(default=40_000, ge=1_000, le=250_000)

    azure_openai_base_url: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str = "gpt-5.6-luna"
    azure_openai_use_entra: bool = False
    azure_openai_reasoning_effort: str = "low"
    azure_openai_timeout_seconds: float = Field(default=3.0, ge=0.5, le=30)
    ai_requests_per_minute: int = Field(default=20, ge=0, le=10_000)
    ai_requests_per_client_minute: int = Field(default=5, ge=0, le=1_000)
    max_concurrent_searches: int = Field(default=4, ge=1, le=32)
    max_request_body_bytes: int = Field(default=16_384, ge=1024, le=1_048_576)
    cors_origins: str = ""

    low_confidence_threshold: float = Field(default=0.31, ge=0, le=1)

    @property
    def ai_configured(self) -> bool:
        has_auth = bool(self.azure_openai_api_key) or self.azure_openai_use_entra
        return bool(self.azure_openai_base_url and self.azure_openai_deployment and has_auth)

    @property
    def allowed_cors_origins(self) -> tuple[str, ...]:
        """Return explicitly configured browser origins without wildcard access."""
        return tuple(
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
