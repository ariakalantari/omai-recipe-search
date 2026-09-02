from recipe_search.durations import parse_duration_minutes, recipe_total_minutes


def test_parses_supported_iso_8601_durations() -> None:
    assert parse_duration_minutes("PT15M") == 15
    assert parse_duration_minutes("PT1H30M") == 90
    assert parse_duration_minutes("pt2h") == 120
    assert parse_duration_minutes("PT0M") == 0


def test_rejects_missing_or_unsupported_durations() -> None:
    assert parse_duration_minutes(None) is None
    assert parse_duration_minutes("") is None
    assert parse_duration_minutes("PT") is None
    assert parse_duration_minutes("P1D") is None
    assert parse_duration_minutes("about 20 minutes") is None


def test_total_requires_both_valid_components() -> None:
    assert recipe_total_minutes("PT15M", "PT1H5M") == 80
    assert recipe_total_minutes("PT15M", None) is None
    assert recipe_total_minutes(None, "PT20M") is None
    assert recipe_total_minutes("unknown", "PT20M") is None
