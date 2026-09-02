from __future__ import annotations

import re

_DURATION = re.compile(r"^PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?$", re.IGNORECASE)


def parse_duration_minutes(value: str | None) -> int | None:
    """Parse the hour and minute subset of ISO 8601 used by the recipe corpus."""
    if not value:
        return None
    match = _DURATION.fullmatch(value.strip())
    if not match or not any(match.group(name) is not None for name in ("hours", "minutes")):
        return None
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    return (hours * 60) + minutes


def recipe_total_minutes(prep_time: str | None, cook_time: str | None) -> int | None:
    """Return a total only when both components are present and valid."""
    prep_minutes = parse_duration_minutes(prep_time)
    cook_minutes = parse_duration_minutes(cook_time)
    if prep_minutes is None or cook_minutes is None:
        return None
    return prep_minutes + cook_minutes
