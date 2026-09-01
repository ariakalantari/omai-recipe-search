from recipe_search.normalization import ingredient_terms, normalize_text, query_ingredients


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
