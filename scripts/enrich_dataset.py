#!/usr/bin/env python3
"""Build a method-complete subset of the OMAI assignment corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from recipe_search.enrichment import MATCHER_VERSION, build_enriched_dataset, report_json


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recipes",
        type=Path,
        default=Path("data/assignment/20170107-061401-recipeitems.jsonl"),
    )
    parser.add_argument("--methods", type=Path, default=Path("data/methods"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/enriched/recipes.jsonl"),
    )
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument("--minimum-coverage", type=float, default=0.9)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/enrichment-manifest.json"),
    )
    args = parser.parse_args()
    report = build_enriched_dataset(
        args.recipes,
        args.methods,
        args.output,
        limit=args.limit,
        minimum_bidirectional_coverage=args.minimum_coverage,
    )
    print(report_json(report))
    method_files = sorted(args.methods.glob("recipes_raw_nosource_*.json"))
    manifest = {
        "matcher_version": MATCHER_VERSION,
        "minimum_bidirectional_coverage": args.minimum_coverage,
        "selection_seed": 20_260_902,
        "inputs": {
            str(args.recipes): sha256(args.recipes),
            **{str(path): sha256(path) for path in method_files},
        },
        "output": {str(args.output): sha256(args.output)},
        "report": json.loads(report_json(report)),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
