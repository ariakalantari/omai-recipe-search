#!/usr/bin/env python3
"""Build and validate all configured local search indexes."""

from recipe_search.config import Settings
from recipe_search.service import build_search_service


def main() -> None:
    settings = Settings()
    service = build_search_service(settings)
    print(
        f"Indexed {len(service.index.recipes):,} recipes; "
        f"semantic_available={service.index.semantic_available}; "
        f"warnings={len(service.load_report.warnings)}"
    )


if __name__ == "__main__":
    main()
