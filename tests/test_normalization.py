from recipe_search.domain import QueryIntent
from recipe_search.normalization import (
    excluded_preference_terms,
    ingredient_terms,
    normalize_text,
    preference_terms,
    query_ingredients,
    query_intent,
    split_excluded_ingredients,
)


def test_normalize_text_removes_accents_and_punctuation() -> None:
    assert normalize_text("  Kokosmjölk, LÖK! ") == "kokosmjolk lok"


def test_ingredient_terms_remove_quantities_units_and_preparation() -> None:
    terms = ingredient_terms("2 tablespoons finely chopped red onions")
    assert "red onion" in terms
    assert "tablespoon" not in terms
    assert "chopped" not in terms


def test_multilingual_food_aliases_are_canonicalized() -> None:
    terms = query_ingredients(["torsk", "kokosmjölk", "lök", "ajo", "tomates"])
    assert {"cod", "coconut milk", "onion", "garlic", "tomato"}.issubset(terms)


def test_query_bigrams_do_not_bridge_conjunctions() -> None:
    terms = query_ingredients(["något starkt med torsk och kokosmjölk"])
    assert terms == ("coconut milk", "cod")
    assert "cod coconut" not in terms


def test_query_bigrams_do_not_bridge_comma_separated_ingredients() -> None:
    positive, _ = split_excluded_ingredients("I have eggs, potatoes and onion")
    assert query_ingredients([positive]) == (
        "egg",
        "onion",
        "potato",
    )


def test_discovery_intent_is_multilingual_and_bounded() -> None:
    assert query_intent("something I haven't had before") is QueryIntent.ADVENTUROUS
    assert query_intent("något annorlunda") is QueryIntent.ADVENTUROUS
    assert query_intent("sorpréndeme con algo nuevo") is QueryIntent.ADVENTUROUS
    assert query_intent("food") is QueryIntent.BROWSE
    assert query_intent("fasting food") is QueryIntent.SEARCH


def test_negation_is_removed_from_positive_ingredients() -> None:
    positive, excluded = split_excluded_ingredients("pasta con tomate sin ajo")
    assert {"pasta", "tomato"}.issubset(query_ingredients([positive]))
    assert "garlic" in excluded


def test_preferences_use_word_boundaries_and_respect_negation() -> None:
    assert preference_terms("hotdog after fasting") == ()
    assert preference_terms("not spicy chicken") == ()
    assert preference_terms("dinner without spicy food") == ()
    assert excluded_preference_terms("not spicy chicken") == ("spicy",)
    assert excluded_preference_terms("middag utan starkt") == ("spicy",)
    assert excluded_preference_terms("cena sin picante") == ("spicy",)
