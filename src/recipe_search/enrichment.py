from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from recipe_search.domain import InstructionSource, Recipe
from recipe_search.loader import _as_text, _ingredients, _instructions, _iter_records, _to_recipe
from recipe_search.normalization import ingredient_terms, normalize_text

MATCHER_VERSION = "exact-title-source-bidirectional-ingredients-v1"


@dataclass(frozen=True, slots=True)
class MethodCandidate:
    instructions: str
    ingredient_terms: frozenset[str]
    corpus: str
    record_key: str


@dataclass(slots=True)
class EnrichmentReport:
    method_records_seen: int = 0
    method_records_loaded: int = 0
    assignment_records_seen: int = 0
    assignment_recipes_usable: int = 0
    title_matches: int = 0
    strict_matches: int = 0
    title_matches_rejected: int = 0
    recipes_selected: int = 0
    method_sources: dict[str, int] | None = None


def recipe_ingredient_terms(ingredients: Sequence[str]) -> frozenset[str]:
    terms: set[str] = set()
    for ingredient in ingredients:
        terms.update(ingredient_terms(ingredient))
    return frozenset(terms)


def method_corpus_name(path: Path) -> str:
    if path.name.endswith("_ar.json"):
        return "recipe_box_allrecipes"
    if path.name.endswith("_epi.json"):
        return "recipe_box_epicurious"
    return f"recipe_box_{path.stem}"


def clean_method_text(value: str) -> str:
    """Remove the duplicated full-method prefix present in the Epicurious export."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return ""

    def comparable(text: str) -> str:
        return re.sub(r"\s+", "", text).casefold()

    if len(lines) > 1 and comparable(lines[0]) == comparable(" ".join(lines[1:])):
        lines = lines[1:]
    deduplicated: list[str] = []
    for line in lines:
        if not deduplicated or comparable(line) != comparable(deduplicated[-1]):
            deduplicated.append(line)
    return "\n".join(deduplicated)


def load_method_lookup(method_data_path: Path) -> dict[str, list[MethodCandidate]]:
    lookup: defaultdict[str, list[MethodCandidate]] = defaultdict(list)
    files = sorted(method_data_path.glob("recipes_raw_nosource_*.json"))
    if not files:
        raise RuntimeError(f"No instruction corpus files found in {method_data_path}")
    for path in files:
        corpus = method_corpus_name(path)
        for key, raw in _iter_records(path):
            if not isinstance(raw, Mapping):
                continue
            title = _as_text(raw.get("title") or raw.get("name"))
            ingredients = _ingredients(raw.get("ingredients"))
            raw_instructions = _instructions(raw.get("instructions"))
            instructions = clean_method_text(raw_instructions or "")
            if not title or not ingredients or not instructions:
                continue
            terms = recipe_ingredient_terms(ingredients)
            if terms:
                lookup[normalize_text(title)].append(
                    MethodCandidate(
                        instructions=instructions,
                        ingredient_terms=terms,
                        corpus=corpus,
                        record_key=key,
                    )
                )
    return dict(lookup)


def match_method(
    recipe: Recipe,
    candidates: Sequence[MethodCandidate],
    *,
    minimum_bidirectional_coverage: float = 0.9,
) -> tuple[MethodCandidate, float] | None:
    """Match only when nearly all ingredient terms agree in both directions."""
    recipe_terms = recipe_ingredient_terms(recipe.ingredients)
    if not recipe_terms:
        return None
    compatible_sources = {
        "recipe_box_allrecipes": {"allrecipes"},
        "recipe_box_epicurious": {"epicurious", "bonappetit"},
    }
    eligible = [
        candidate
        for candidate in candidates
        if recipe.source in compatible_sources.get(candidate.corpus, set())
    ]
    if not eligible:
        return None
    ranked: list[tuple[float, float, MethodCandidate]] = []
    for candidate in eligible:
        shared = len(recipe_terms.intersection(candidate.ingredient_terms))
        recipe_coverage = shared / len(recipe_terms)
        method_coverage = shared / len(candidate.ingredient_terms)
        ranked.append(
            (
                min(recipe_coverage, method_coverage),
                (recipe_coverage + method_coverage) / 2,
                candidate,
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_minimum, _best_average, best = ranked[0]
    if best_minimum < minimum_bidirectional_coverage:
        return None
    passing_methods = {
        candidate.instructions
        for minimum, _average, candidate in ranked
        if minimum >= minimum_bidirectional_coverage
    }
    if len(passing_methods) > 1:
        return None
    return best, best_minimum


def enriched_record(
    recipe: Recipe,
    candidate: MethodCandidate,
    *,
    assignment_record: str,
) -> dict[str, Any]:
    return {
        "name": recipe.name,
        "ingredients": list(recipe.ingredients),
        "source": recipe.source,
        "url": recipe.url,
        "image": recipe.image_url,
        "prepTime": recipe.prep_time,
        "cookTime": recipe.cook_time,
        "recipeYield": recipe.recipe_yield,
        "description": recipe.description,
        "recipeInstructions": candidate.instructions,
        "instructionSource": InstructionSource.MATCHED_CORPUS,
        "instructionCorpus": candidate.corpus,
        "instructionRecord": candidate.record_key,
        "assignmentRecord": assignment_record,
        "instructionMatcher": MATCHER_VERSION,
    }


def build_enriched_dataset(
    assignment_path: Path,
    method_data_path: Path,
    output_path: Path,
    *,
    limit: int,
    minimum_bidirectional_coverage: float = 0.9,
    seed: int = 20_260_902,
) -> EnrichmentReport:
    if limit < 1:
        raise ValueError("limit must be positive")
    method_lookup = load_method_lookup(method_data_path)
    report = EnrichmentReport(
        method_records_loaded=sum(len(candidates) for candidates in method_lookup.values())
    )
    report.method_records_seen = report.method_records_loaded
    selected: list[dict[str, Any]] = []
    matched_seen = 0
    rng = random.Random(seed)
    source_counts: Counter[str] = Counter()

    for key, raw in _iter_records(assignment_path):
        report.assignment_records_seen += 1
        recipe = _to_recipe(raw, key, assignment_path)
        if recipe is None:
            continue
        report.assignment_recipes_usable += 1
        candidates = method_lookup.get(normalize_text(recipe.name))
        if not candidates:
            continue
        report.title_matches += 1
        matched = match_method(
            recipe,
            candidates,
            minimum_bidirectional_coverage=minimum_bidirectional_coverage,
        )
        if matched is None:
            report.title_matches_rejected += 1
            continue
        candidate, score = matched
        report.strict_matches += 1
        matched_seen += 1
        record = enriched_record(recipe, candidate, assignment_record=key)
        record["instructionMatchScore"] = round(score, 6)
        if len(selected) < limit:
            selected.append(record)
        else:
            replacement = rng.randrange(matched_seen)
            if replacement < limit:
                selected[replacement] = record

    if len(selected) < limit:
        raise RuntimeError(
            f"Only {len(selected)} high-confidence instruction matches were available; "
            f"{limit} were required"
        )
    rng.shuffle(selected)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
            source_counts[str(record["instructionCorpus"])] += 1
    temporary_path.replace(output_path)
    report.recipes_selected = len(selected)
    report.method_sources = dict(sorted(source_counts.items()))
    return report


def report_json(report: EnrichmentReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True)
