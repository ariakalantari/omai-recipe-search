from __future__ import annotations

import json
from pathlib import Path

from recipe_search.domain import Recipe
from recipe_search.enrichment import (
    MethodCandidate,
    build_enriched_dataset,
    clean_method_text,
    match_method,
    recipe_ingredient_terms,
)
from recipe_search.loader import load_recipes


def candidate(
    ingredients: tuple[str, ...],
    instructions: str = "Cook carefully.",
    corpus: str = "recipe_box_allrecipes",
    key: str = "method-1",
) -> MethodCandidate:
    return MethodCandidate(
        instructions=instructions,
        ingredient_terms=recipe_ingredient_terms(ingredients),
        corpus=corpus,
        record_key=key,
    )


def test_match_requires_exact_source_family_and_bidirectional_coverage() -> None:
    recipe = Recipe(
        id="one",
        name="Tomato Soup",
        ingredients=("tomato", "onion", "garlic", "stock"),
        source="allrecipes",
    )
    strong = candidate(("tomato", "onion", "garlic", "stock"))
    wrong_source = candidate(
        ("tomato", "onion", "garlic", "stock"),
        corpus="recipe_box_epicurious",
    )
    extra_terms = candidate(("tomato", "onion", "garlic", "stock", "cream", "basil"))

    assert match_method(recipe, [strong]) == (strong, 1.0)
    assert match_method(recipe, [wrong_source]) is None
    assert match_method(recipe, [extra_terms]) is None


def test_match_rejects_ambiguous_distinct_methods() -> None:
    recipe = Recipe(
        id="one",
        name="Simple Syrup",
        ingredients=("sugar", "water"),
        source="allrecipes",
    )
    first = candidate(("sugar", "water"), instructions="Boil together.", key="one")
    second = candidate(("sugar", "water"), instructions="Stir without boiling.", key="two")
    duplicate = candidate(("sugar", "water"), instructions="Boil together.", key="three")

    assert match_method(recipe, [first, second]) is None
    assert match_method(recipe, [first, duplicate]) == (first, 1.0)


def test_method_cleanup_keeps_steps_and_removes_export_duplication() -> None:
    full = "Heat the pan. Add the beans. Serve."
    duplicated = f"{full}\nHeat the pan.\nAdd the beans.\nServe."

    assert clean_method_text(duplicated) == "Heat the pan.\nAdd the beans.\nServe."
    assert clean_method_text(f"{full}\n{full}") == full


def test_enriched_output_is_deterministic_and_method_complete(tmp_path: Path) -> None:
    assignment = tmp_path / "assignment.jsonl"
    assignment.write_text(
        "\n".join(
            json.dumps(
                {
                    "name": f"Tomato Soup {index}",
                    "ingredients": ["2 tomatoes", "1 onion", "1 cup stock"],
                    "source": "allrecipes",
                    "url": f"https://example.com/{index}",
                }
            )
            for index in range(4)
        ),
        encoding="utf-8",
    )
    methods = tmp_path / "methods"
    methods.mkdir()
    method_records = {
        str(index): {
            "title": f"Tomato Soup {index}",
            "ingredients": ["tomatoes", "onion", "stock"],
            "instructions": f"Cook soup {index}.\nServe soup {index}.",
        }
        for index in range(4)
    }
    (methods / "recipes_raw_nosource_ar.json").write_text(
        json.dumps(method_records), encoding="utf-8"
    )
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"

    first_report = build_enriched_dataset(assignment, methods, first, limit=3)
    second_report = build_enriched_dataset(assignment, methods, second, limit=3)
    recipes, _, _ = load_recipes(first)

    assert first.read_bytes() == second.read_bytes()
    assert first_report.strict_matches == second_report.strict_matches == 4
    assert len(recipes) == 3
    assert all(recipe.instructions for recipe in recipes)
    assert all(recipe.instruction_source == "matched_corpus" for recipe in recipes)
