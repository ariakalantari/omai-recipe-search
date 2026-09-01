from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, ClassVar, Protocol

from recipe_search.config import Settings
from recipe_search.domain import InterpretedQuery, QueryKind
from recipe_search.normalization import preference_terms, query_ingredients

logger = logging.getLogger(__name__)


class QueryInterpreter(Protocol):
    @property
    def available(self) -> bool: ...

    async def interpret(self, query: str) -> InterpretedQuery: ...


class HeuristicQueryInterpreter:
    available = True

    async def interpret(self, query: str) -> InterpretedQuery:
        return self.interpret_sync(query)

    def interpret_sync(
        self,
        query: str,
        *,
        kind: QueryKind = QueryKind.NATURAL_LANGUAGE,
    ) -> InterpretedQuery:
        return InterpretedQuery(
            original=query,
            kind=kind,
            ingredients=query_ingredients([query]),
            preferences=preference_terms(query),
            source="heuristic",
        )

    def from_ingredients(self, ingredients: list[str]) -> InterpretedQuery:
        original = ", ".join(ingredients)
        return InterpretedQuery(
            original=original,
            kind=QueryKind.INGREDIENTS,
            ingredients=query_ingredients(ingredients),
            source="deterministic",
        )


class AzureOpenAIQueryInterpreter:
    """Narrow Azure adapter: free text in, validated query structure out."""

    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ingredients": {"type": "array", "items": {"type": "string"}},
            "excluded_ingredients": {"type": "array", "items": {"type": "string"}},
            "preferences": {"type": "array", "items": {"type": "string"}},
            "max_minutes": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        },
        "required": ["ingredients", "excluded_ingredients", "preferences", "max_minutes"],
    }

    def __init__(self, settings: Settings, fallback: HeuristicQueryInterpreter) -> None:
        self._settings = settings
        self._fallback = fallback

    @property
    def available(self) -> bool:
        return self._settings.ai_configured

    def _client(self) -> Any:
        from openai import OpenAI

        api_key = self._settings.azure_openai_api_key
        if not api_key:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://ai.azure.com/.default"
            )
            api_key = token_provider()
        return OpenAI(
            api_key=api_key,
            base_url=self._settings.azure_openai_base_url,
            timeout=self._settings.azure_openai_timeout_seconds,
            max_retries=0,
        )

    def _interpret_sync(self, query: str) -> InterpretedQuery:
        client = self._client()
        response = client.responses.create(
            model=self._settings.azure_openai_deployment,
            store=False,
            reasoning={"effort": self._settings.azure_openai_reasoning_effort},
            max_output_tokens=300,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Extract cooking search constraints. Translate ingredient names to concise "
                        "English singular forms. Preferences may include spicy, quick, vegetarian, "
                        "vegan, cuisine, or dish style. Never suggest recipes and never add an "
                        "ingredient the user did not mention."
                    ),
                },
                {"role": "user", "content": query},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "recipe_query",
                    "strict": True,
                    "schema": self._SCHEMA,
                }
            },
        )
        payload = json.loads(response.output_text)
        ingredients = tuple(
            str(value).strip() for value in payload["ingredients"] if str(value).strip()
        )
        excluded = tuple(
            str(value).strip() for value in payload["excluded_ingredients"] if str(value).strip()
        )
        preferences = tuple(
            str(value).strip() for value in payload["preferences"] if str(value).strip()
        )
        max_minutes = payload["max_minutes"]
        return InterpretedQuery(
            original=query,
            kind=QueryKind.NATURAL_LANGUAGE,
            ingredients=ingredients,
            excluded_ingredients=excluded,
            preferences=preferences,
            max_minutes=max_minutes if isinstance(max_minutes, int) and max_minutes > 0 else None,
            source="azure_openai",
        )

    async def interpret(self, query: str) -> InterpretedQuery:
        if not self.available:
            return await self._fallback.interpret(query)
        try:
            return await asyncio.to_thread(self._interpret_sync, query)
        except Exception as exc:  # provider and validation failures share the same fallback
            logger.warning(
                "Azure query interpretation failed; using heuristic fallback: %s",
                type(exc).__name__,
            )
            fallback = await self._fallback.interpret(query)
            return InterpretedQuery(
                original=fallback.original,
                kind=fallback.kind,
                ingredients=fallback.ingredients,
                excluded_ingredients=fallback.excluded_ingredients,
                preferences=fallback.preferences,
                max_minutes=fallback.max_minutes,
                source=fallback.source,
                degraded=True,
                warning="AI query interpretation was unavailable; deterministic fallback used.",
            )
