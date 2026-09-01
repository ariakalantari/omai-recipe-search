from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import ijson

from recipe_search.domain import LoadReport, Recipe


class DatasetError(RuntimeError):
    """Raised when no usable dataset can be loaded."""


def resolve_data_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(candidate for candidate in path.glob("*.json*") if candidate.is_file())
    raise DatasetError(f"Recipe data path does not exist: {path}")


def dataset_fingerprint(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode())
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()[:16]


def _iter_records(path: Path) -> Iterator[tuple[str, Any]]:
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if line.strip():
                    yield str(index), json.loads(line)
        return

    with path.open("rb") as handle:
        first_character = ""
        while byte := handle.read(1):
            character = byte.decode("utf-8")
            if not character.isspace():
                first_character = character
                break
        handle.seek(0)
        if first_character == "{":
            yield from ((str(key), value) for key, value in ijson.kvitems(handle, ""))
        elif first_character == "[":
            yield from (
                (str(index), value) for index, value in enumerate(ijson.items(handle, "item"))
            )
        else:
            raise DatasetError(f"Unsupported JSON root in {path}: {first_character!r}")


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ingredients(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        candidates = value.splitlines()
    elif isinstance(value, list):
        candidates = [str(item) for item in value if item is not None]
    else:
        return ()
    cleaned: list[str] = []
    for candidate in candidates:
        line = candidate.replace("ADVERTISEMENT", "").strip(" \t,-")
        if line:
            cleaned.append(line)
    return tuple(cleaned)


def _safe_url(value: Any) -> str | None:
    text = _as_text(value)
    if not text:
        return None
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _source(record: Mapping[str, Any], path: Path, url: str | None) -> str | None:
    explicit = _as_text(record.get("source"))
    if explicit:
        return explicit
    if url:
        return urlparse(url).netloc.removeprefix("www.")
    stem = path.stem
    return stem if stem != "sample_recipes" else "sample"


def _to_recipe(record: Any, key: str, path: Path) -> Recipe | None:
    if not isinstance(record, Mapping):
        return None
    name = _as_text(record.get("name") or record.get("title"))
    ingredients = _ingredients(
        record.get("ingredients")
        or record.get("recipeIngredient")
        or record.get("ingredient_lines")
    )
    if not name or not ingredients:
        return None
    url = _safe_url(record.get("url") or record.get("source_url") or record.get("link"))
    image = _safe_url(record.get("image") or record.get("image_url") or record.get("picture_link"))
    stable_key = f"{path.name}:{key}:{name}"
    recipe_id = hashlib.sha1(stable_key.encode(), usedforsecurity=False).hexdigest()[:16]
    return Recipe(
        id=recipe_id,
        name=name,
        ingredients=ingredients,
        source=_source(record, path, url),
        url=url,
        image_url=image,
        prep_time=_as_text(record.get("prepTime") or record.get("prep_time")),
        cook_time=_as_text(record.get("cookTime") or record.get("cook_time")),
        recipe_yield=_as_text(record.get("recipeYield") or record.get("yield")),
        description=_as_text(record.get("description")),
    )


def load_recipes(
    path: Path, max_recipes: int | None = None
) -> tuple[list[Recipe], LoadReport, str]:
    files = resolve_data_files(path)
    if not files:
        raise DatasetError(f"No JSON files found in: {path}")
    report = LoadReport(files=len(files))
    recipes: list[Recipe] = []
    for file_path in files:
        try:
            for key, record in _iter_records(file_path):
                report.records_seen += 1
                recipe = _to_recipe(record, key, file_path)
                if recipe is None:
                    report.records_skipped += 1
                    continue
                recipes.append(recipe)
                if max_recipes is not None and len(recipes) >= max_recipes:
                    break
        except (OSError, UnicodeError, json.JSONDecodeError, ijson.JSONError, DatasetError) as exc:
            report.warnings.append(f"Skipped {file_path.name}: {exc}")
        if max_recipes is not None and len(recipes) >= max_recipes:
            break
    if not recipes:
        raise DatasetError("The dataset contained no usable recipes.")
    report.recipes_loaded = len(recipes)
    return recipes, report, dataset_fingerprint(files)
