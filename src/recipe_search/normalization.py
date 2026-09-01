from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from itertools import pairwise

_NUMBER = re.compile(r"\b\d+(?:[./]\d+)?\b")
_PUNCTUATION = re.compile(r"[^a-z0-9\s-]")
_WHITESPACE = re.compile(r"\s+")

_UNITS = {
    "cup",
    "cups",
    "tablespoon",
    "tablespoons",
    "tbsp",
    "teaspoon",
    "teaspoons",
    "tsp",
    "ounce",
    "ounces",
    "oz",
    "pound",
    "pounds",
    "lb",
    "lbs",
    "gram",
    "grams",
    "kg",
    "ml",
    "liter",
    "liters",
    "pinch",
    "dash",
    "package",
    "packages",
    "can",
    "cans",
    "clove",
    "cloves",
    "slice",
    "slices",
    "piece",
    "pieces",
    "small",
    "medium",
    "large",
}

_PREPARATION_WORDS = {
    "chopped",
    "diced",
    "minced",
    "sliced",
    "peeled",
    "crushed",
    "ground",
    "fresh",
    "finely",
    "roughly",
    "optional",
    "divided",
    "melted",
    "softened",
    "cooked",
    "uncooked",
    "to",
    "taste",
    "and",
    "or",
    "for",
    "serving",
    "advertisement",
}

_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "anything",
    "cook",
    "dish",
    "food",
    "have",
    "i",
    "in",
    "make",
    "meal",
    "med",
    "me",
    "my",
    "nagot",
    "något",
    "of",
    "please",
    "recipe",
    "something",
    "the",
    "want",
    "with",
    "och",
    "con",
    "de",
    "y",
    "que",
    "quiero",
}

_PREFERENCE_WORDS = {
    "comfort",
    "easy",
    "fast",
    "healthy",
    "quick",
    "spicy",
    "starkt",
    "vegetarian",
    "vegetarisk",
    "picante",
}

_PHRASE_ALIASES = {
    "leche de coco": "coconut milk",
    "kokos mjolk": "coconut milk",
    "kokosmjolk": "coconut milk",
    "chili pepper": "chili",
}

_TOKEN_ALIASES = {
    # Swedish
    "agg": "egg",
    "ägg": "egg",
    "fisk": "fish",
    "kyckling": "chicken",
    "lax": "salmon",
    "lok": "onion",
    "lök": "onion",
    "potatis": "potato",
    "torsk": "cod",
    "tomat": "tomato",
    "vitlok": "garlic",
    "vitlök": "garlic",
    # Spanish
    "ajo": "garlic",
    "cebolla": "onion",
    "huevo": "egg",
    "huevos": "egg",
    "patata": "potato",
    "patatas": "potato",
    "pollo": "chicken",
    "pescado": "fish",
    "tomate": "tomato",
    "tomates": "tomato",
    # Common English plurals / variants
    "eggs": "egg",
    "onions": "onion",
    "potatoes": "potato",
    "tomatoes": "tomato",
    "chillies": "chili",
    "chilies": "chili",
}


def normalize_text(value: str) -> str:
    """Case-fold, remove accents/punctuation, and normalize whitespace."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    ascii_text = ascii_text.replace("½", " 1/2 ").replace("¼", " 1/4 ").replace("¾", " 3/4 ")
    return _WHITESPACE.sub(" ", _PUNCTUATION.sub(" ", ascii_text)).strip()


def canonicalize_known_foods(value: str) -> str:
    normalized = normalize_text(value)
    for source, target in _PHRASE_ALIASES.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    return " ".join(_TOKEN_ALIASES.get(token, token) for token in normalized.split())


def _singularize(token: str) -> str:
    if token in _TOKEN_ALIASES:
        return _TOKEN_ALIASES[token]
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("oes"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def ingredient_terms(value: str, *, query: bool = False) -> frozenset[str]:
    """Extract explainable unigram and adjacent-bigram ingredient terms."""
    normalized = canonicalize_known_foods(_NUMBER.sub(" ", value))
    ignored = _UNITS | _PREPARATION_WORDS
    if query:
        ignored |= _QUERY_STOPWORDS | _PREFERENCE_WORDS
    words = [
        _singularize(word) for word in normalized.split() if len(word) > 1 and word not in ignored
    ]
    terms = set(words)
    terms.update(f"{left} {right}" for left, right in pairwise(words))
    return frozenset(terms)


def query_ingredients(values: Iterable[str]) -> tuple[str, ...]:
    """Return stable, canonical ingredient terms from one or more inputs."""
    terms: set[str] = set()
    for value in values:
        terms.update(ingredient_terms(value, query=True))
    # Prefer informative phrases but keep unigrams for partial matching.
    return tuple(sorted(terms, key=lambda item: (-item.count(" "), item)))


def preference_terms(value: str) -> tuple[str, ...]:
    normalized = normalize_text(value)
    found: list[str] = []
    mappings = {
        "spicy": ("spicy", "starkt", "picante", "hot"),
        "quick": ("quick", "fast", "snabbt", "rapido", "rápido"),
        "vegetarian": ("vegetarian", "vegetarisk", "vegetariano", "vegetariana"),
        "comfort food": ("comfort food", "comfort", "husmanskost"),
    }
    for canonical, aliases in mappings.items():
        if any(normalize_text(alias) in normalized for alias in aliases):
            found.append(canonical)
    return tuple(found)
