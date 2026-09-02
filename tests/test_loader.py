from __future__ import annotations

import json
from pathlib import Path

import pytest

from recipe_search.loader import DatasetError, load_recipes


def test_loader_accepts_name_and_title_and_skips_bad_records(tmp_path: Path) -> None:
    data = {
        "one": {
            "title": "Soup",
            "ingredients": ["1 onion ADVERTISEMENT", "ADVERTISEMENT"],
            "recipeInstructions": [
                {"text": "Chop the onion."},
                {"text": "Simmer until tender."},
            ],
        },
        "two": {
            "name": "Pasta",
            "ingredients": "tomato\ngarlic",
            "url": "https://example.com/pasta",
        },
        "bad": {"name": "Missing ingredients"},
    }
    path = tmp_path / "recipes.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    recipes, report, fingerprint = load_recipes(path)
    assert [recipe.name for recipe in recipes] == ["Soup", "Pasta"]
    assert recipes[0].ingredients == ("1 onion",)
    assert recipes[0].instructions == "Chop the onion.\nSimmer until tender."
    assert recipes[0].instruction_source == "dataset"
    assert report.records_skipped == 1
    assert len(fingerprint) == 16


def test_loader_decodes_source_html_entities(tmp_path: Path) -> None:
    path = tmp_path / "recipes.jsonl"
    path.write_text(
        json.dumps(
            {
                "name": "Fish &amp; Chips",
                "ingredients": "cod\nsalt &amp; pepper",
                "description": "&amp;quot;A classic&amp;quot;",
            }
        ),
        encoding="utf-8",
    )

    recipes, _, _ = load_recipes(path)

    assert recipes[0].name == "Fish & Chips"
    assert recipes[0].ingredients == ("cod", "salt & pepper")
    assert recipes[0].description == '"A classic"'


def test_loader_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="does not exist"):
        load_recipes(tmp_path / "missing.json")


def test_capped_directory_load_is_balanced_across_files(tmp_path: Path) -> None:
    for prefix in ("alpha", "beta"):
        records = [
            {"name": f"{prefix}-{index}", "ingredients": [f"ingredient-{index}"]}
            for index in range(4)
        ]
        (tmp_path / f"{prefix}.json").write_text(json.dumps(records), encoding="utf-8")

    recipes, _, _ = load_recipes(tmp_path, max_recipes=4)
    assert [recipe.name for recipe in recipes] == ["alpha-0", "beta-0", "alpha-1", "beta-1"]


def test_capped_single_file_samples_the_full_stream_deterministically(tmp_path: Path) -> None:
    records = [
        {
            "name": f"recipe-{index}",
            "ingredients": [f"ingredient-{index}"],
            "description": f"Description {index}",
        }
        for index in range(40)
    ]
    path = tmp_path / "recipes.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    first, report, _ = load_recipes(path, max_recipes=5)
    second, _, _ = load_recipes(path, max_recipes=5)

    assert [recipe.name for recipe in first] == [recipe.name for recipe in second]
    assert any(int(recipe.name.removeprefix("recipe-")) >= 5 for recipe in first)
    assert all(recipe.description for recipe in first)
    assert report.records_seen == 40
    assert report.recipes_loaded == 5
