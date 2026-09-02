from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SearchMode(StrEnum):
    HYBRID = "hybrid"
    LEXICAL = "lexical"
    SEMANTIC = "semantic"


class QueryKind(StrEnum):
    NATURAL_LANGUAGE = "natural_language"
    INGREDIENTS = "ingredients"


class QueryIntent(StrEnum):
    SEARCH = "search"
    ADVENTUROUS = "adventurous"
    BROWSE = "browse"


class SearchStrategy(StrEnum):
    SEARCH = "search"
    ADVENTUROUS = "adventurous"
    DISCOVERY = "discovery"


class InstructionSource(StrEnum):
    DATASET = "dataset"
    MATCHED_CORPUS = "matched_corpus"


@dataclass(frozen=True, slots=True)
class Recipe:
    id: str
    name: str
    ingredients: tuple[str, ...]
    source: str | None = None
    url: str | None = None
    image_url: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    recipe_yield: str | None = None
    description: str | None = None
    instructions: str | None = None
    instruction_source: InstructionSource | None = None

    @property
    def search_text(self) -> str:
        parts = [self.name, *self.ingredients]
        if self.description:
            parts.append(self.description)
        return "\n".join(parts)


@dataclass(frozen=True, slots=True)
class InterpretedQuery:
    original: str
    kind: QueryKind
    intent: QueryIntent = QueryIntent.SEARCH
    ingredients: tuple[str, ...] = ()
    excluded_ingredients: tuple[str, ...] = ()
    preferences: tuple[str, ...] = ()
    excluded_preferences: tuple[str, ...] = ()
    max_minutes: int | None = None
    source: str = "heuristic"
    degraded: bool = False
    warning: str | None = None

    @property
    def semantic_text(self) -> str:
        additions = [*self.ingredients, *self.preferences]
        if not additions:
            return self.original
        if self.excluded_ingredients or self.excluded_preferences:
            return f"Desired: {', '.join(additions)}"
        return f"{self.original}. Desired: {', '.join(additions)}"


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    final: float
    semantic: float | None
    lexical: float
    ingredient: float
    distinctiveness: float
    matched_ingredients: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RankedRecipe:
    recipe: Recipe
    scores: ScoreBreakdown


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    results: tuple[RankedRecipe, ...]
    strategy: SearchStrategy
    semantic_degraded: bool = False
    warning: str | None = None


@dataclass(slots=True)
class LoadReport:
    files: int = 0
    records_seen: int = 0
    recipes_loaded: int = 0
    records_skipped: int = 0
    warnings: list[str] = field(default_factory=list)
