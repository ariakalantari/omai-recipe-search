from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from recipe_search.config import Settings
from recipe_search.domain import SearchMode
from recipe_search.normalization import canonicalize_known_foods, normalize_text
from recipe_search.schemas import SearchRequest
from recipe_search.service import build_search_service


@dataclass(frozen=True)
class EvaluationRow:
    query_id: str
    query: str
    note: str
    mode: str
    top_result: str
    first_relevant_rank: int | None
    confidence: str
    answerable: bool


def relevant(text: str, expected: list[str], minimum_matches: int) -> bool:
    normalized = canonicalize_known_foods(text)
    matches = sum(normalize_text(term) in normalized for term in expected)
    return minimum_matches > 0 and matches >= minimum_matches


async def evaluate(settings: Settings, query_path: Path, top_k: int) -> list[EvaluationRow]:
    service = build_search_service(settings)
    cases: list[dict[str, Any]] = json.loads(query_path.read_text(encoding="utf-8"))
    rows: list[EvaluationRow] = []
    for case in cases:
        answerable = any(
            relevant(
                recipe.search_text,
                case["expected_any"],
                case.get("minimum_matches", 1),
            )
            for recipe in service.index.recipes
        )
        for mode in SearchMode:
            request = SearchRequest(
                query=case.get("query"),
                ingredients=case.get("ingredients"),
                mode=mode,
                limit=top_k,
                ai="off",
            )
            response = await service.search(request, client_id="evaluation")
            rank = next(
                (
                    index
                    for index, recipe in enumerate(response.results, start=1)
                    if relevant(
                        f"{recipe.name} {' '.join(recipe.ingredients)}",
                        case["expected_any"],
                        case.get("minimum_matches", 1),
                    )
                ),
                None,
            )
            rows.append(
                EvaluationRow(
                    query_id=case["id"],
                    query=case.get("query") or ", ".join(case["ingredients"]),
                    note=case["note"],
                    mode=mode,
                    top_result=response.results[0].name if response.results else "—",
                    first_relevant_rank=rank,
                    confidence=response.meta.confidence,
                    answerable=answerable,
                )
            )
    return rows


def markdown_report(rows: list[EvaluationRow], top_k: int) -> str:
    lines = [
        "# Retrieval evaluation",
        "",
        f"A relevant result is counted when the case's minimum number of hand-written theme terms appears in the top {top_k}.",
        "The impossible query has no relevance label and is inspected through its confidence.",
        "",
        "| Query | Mode | Top result | First relevant rank | Confidence |",
        "|---|---|---|---:|---|",
    ]
    for row in rows:
        rank = (
            "n/a"
            if not row.answerable
            else str(row.first_relevant_rank)
            if row.first_relevant_rank is not None
            else "—"
        )
        lines.append(
            f"| {row.query.replace('|', '/')} | {row.mode} | "
            f"{row.top_result.replace('|', '/')} | {rank} | {row.confidence} |"
        )

    lines.extend(["", "## Aggregate (labeled queries)", ""])
    for mode in SearchMode:
        labeled = [row for row in rows if row.mode == mode and row.answerable]
        hits = [row for row in labeled if row.first_relevant_rank is not None]
        hit_rate = len(hits) / len(labeled) if labeled else 0.0
        mrr = (
            sum(1 / row.first_relevant_rank for row in hits if row.first_relevant_rank)
            / len(labeled)
            if labeled
            else 0.0
        )
        lines.append(f"- **{mode}**: Hit@{top_k} {hit_rate:.0%}, MRR {mrr:.3f}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/sample_recipes.json"))
    parser.add_argument("--queries", type=Path, default=Path("evaluation/queries.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-recipes", type=int)
    parser.add_argument("--no-semantic", action="store_true")
    args = parser.parse_args()
    settings = Settings(
        recipe_data_path=args.data,
        max_recipes=args.max_recipes,
        semantic_enabled=not args.no_semantic,
    )
    rows = asyncio.run(evaluate(settings, args.queries, args.top_k))
    report = markdown_report(rows, args.top_k)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
