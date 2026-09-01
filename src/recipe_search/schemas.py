from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from recipe_search.domain import InterpretedQuery, RankedRecipe, SearchMode, SearchStrategy
from recipe_search.summaries import recipe_summary

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    ] = None
    ingredients: list[ShortText] | None = Field(default=None, min_length=1, max_length=20)
    limit: int = Field(default=10, ge=1, le=50)
    mode: SearchMode = SearchMode.HYBRID
    ai: Literal["auto", "off"] = "auto"

    @field_validator("query")
    @classmethod
    def query_has_searchable_text(cls, value: str | None) -> str | None:
        if value is not None and not any(character.isalnum() for character in value):
            raise ValueError("Use at least one letter or number in the query.")
        return value

    @field_validator("ingredients")
    @classmethod
    def ingredients_have_searchable_text(cls, values: list[str] | None) -> list[str] | None:
        if values is not None and any(
            not any(character.isalnum() for character in value) for value in values
        ):
            raise ValueError("Each ingredient must contain at least one letter or number.")
        return values

    @model_validator(mode="after")
    def exactly_one_input(self) -> SearchRequest:
        if (self.query is None) == (self.ingredients is None):
            raise ValueError("Provide exactly one of 'query' or 'ingredients'.")
        return self


class ScoreResponse(BaseModel):
    final: float
    semantic: float | None
    lexical: float
    ingredient: float
    distinctiveness: float


class MatchReasonResponse(BaseModel):
    summary: str
    matched_ingredients: list[str]
    scores: ScoreResponse


class RecipeResponse(BaseModel):
    id: str
    name: str
    ingredients: list[str]
    source: str | None
    url: str | None
    image_url: str | None
    prep_time: str | None
    cook_time: str | None
    recipe_yield: str | None
    description: str | None
    summary: str
    instructions: str | None
    score: float
    match_reason: MatchReasonResponse

    @classmethod
    def from_ranked(
        cls,
        ranked: RankedRecipe,
        strategy: SearchStrategy = SearchStrategy.SEARCH,
    ) -> RecipeResponse:
        recipe = ranked.recipe
        scores = ranked.scores
        matched = list(scores.matched_ingredients)
        if strategy is SearchStrategy.ADVENTUROUS:
            summary = "Adventurous pick with a less common ingredient combination"
        elif strategy is SearchStrategy.DISCOVERY:
            summary = "Varied discovery pick from the recipe collection"
        elif matched:
            summary = f"Matches {', '.join(matched[:4])}"
        elif scores.semantic is not None and scores.semantic >= scores.lexical:
            summary = "Strong meaning-based match"
        elif scores.lexical > 0:
            summary = "Matches words in the request"
        else:
            summary = "Closest available match"
        return cls(
            id=recipe.id,
            name=recipe.name,
            ingredients=list(recipe.ingredients),
            source=recipe.source,
            url=recipe.url,
            image_url=recipe.image_url,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            recipe_yield=recipe.recipe_yield,
            description=recipe.description,
            summary=recipe_summary(recipe),
            instructions=recipe.instructions,
            score=round(scores.final, 4),
            match_reason=MatchReasonResponse(
                summary=summary,
                matched_ingredients=matched,
                scores=ScoreResponse(
                    final=round(scores.final, 4),
                    semantic=None if scores.semantic is None else round(scores.semantic, 4),
                    lexical=round(scores.lexical, 4),
                    ingredient=round(scores.ingredient, 4),
                    distinctiveness=round(scores.distinctiveness, 4),
                ),
            ),
        )


class QueryUnderstandingResponse(BaseModel):
    kind: str
    intent: str
    ingredients: list[str]
    excluded_ingredients: list[str]
    preferences: list[str]
    excluded_preferences: list[str]
    max_minutes: int | None
    source: str
    degraded: bool
    warning: str | None

    @classmethod
    def from_domain(cls, query: InterpretedQuery) -> QueryUnderstandingResponse:
        return cls(
            kind=query.kind,
            intent=query.intent,
            ingredients=list(query.ingredients),
            excluded_ingredients=list(query.excluded_ingredients),
            preferences=list(query.preferences),
            excluded_preferences=list(query.excluded_preferences),
            max_minutes=query.max_minutes,
            source=query.source,
            degraded=query.degraded,
            warning=query.warning,
        )


class SearchMetaResponse(BaseModel):
    mode: str
    strategy: str
    total_recipes: int
    returned: int
    confidence: Literal["high", "medium", "low"]
    semantic_available: bool
    semantic_degraded: bool
    ai_available: bool
    retrieval_warning: str | None
    query_understanding: QueryUnderstandingResponse


class SearchResponse(BaseModel):
    query: str
    results: list[RecipeResponse]
    meta: SearchMetaResponse


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    recipes: int
    semantic_available: bool
    ai_available: bool
    load_warnings: list[str]
