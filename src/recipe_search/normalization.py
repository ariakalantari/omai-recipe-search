from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from itertools import pairwise

from recipe_search.domain import QueryIntent

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
    "adventurous",
    "algo",
    "any",
    "anything",
    "cook",
    "dish",
    "food",
    "before",
    "different",
    "do",
    "eaten",
    "ever",
    "had",
    "have",
    "haven",
    "i",
    "know",
    "in",
    "new",
    "no",
    "not",
    "make",
    "meal",
    "med",
    "me",
    "mig",
    "my",
    "nagot",
    "något",
    "of",
    "please",
    "recipe",
    "something",
    "surprise",
    "the",
    "tried",
    "try",
    "unusual",
    "want",
    "whatever",
    "with",
    "without",
    "och",
    "annorlunda",
    "forut",
    "har",
    "inte",
    "jag",
    "nytt",
    "overraska",
    "utan",
    "con",
    "de",
    "diferente",
    "haya",
    "nuevo",
    "probado",
    "sin",
    "sorprendeme",
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
    "mjolk": "milk",
    "mjölk": "milk",
    "notter": "nut",
    "nötter": "nut",
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
    "nueces": "nut",
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

_ADVENTUROUS_PHRASES = (
    "surprise me",
    "something new",
    "something different",
    "something unusual",
    "something adventurous",
    "never tried",
    "have not tried",
    "haven t tried",
    "have not had",
    "haven t had",
    "not had before",
    "nagot nytt",
    "nagot annorlunda",
    "overraska mig",
    "inte har atit forut",
    "algo nuevo",
    "algo diferente",
    "sorprendeme",
    "no haya probado",
)

_BROWSE_PHRASES = (
    "anything",
    "anything is fine",
    "whatever",
    "food",
    "i do not know",
    "i don t know",
    "i dont know",
    "no preference",
    "vad som helst",
    "jag vet inte",
    "cualquier cosa",
    "no se",
)

_NEGATION_PATTERN = re.compile(
    r"\b(?:without|excluding|exclude|except for|avoid|utan|sin)\b\s+"
    r"(?P<items>.*?)(?=\b(?:with|med|con|but|men|pero)\b|[.;]|$)"
)
_SHORT_NEGATION_PATTERN = re.compile(
    r"\b(?:no|not)\b\s+(?P<items>[a-z0-9-]+(?:\s+(?:and|or|och|y)\s+[a-z0-9-]+)?)"
)

_DISTINCTIVE_NOISE = {
    "about",
    "amount",
    "brand",
    "can",
    "each",
    "free",
    "from",
    "fully",
    "half",
    "inch",
    "less",
    "like",
    "note",
    "package",
    "regular",
    "see",
    "sheet",
    "some",
    "such",
    "use",
}

_PANTRY_STAPLES = {
    "baking powder",
    "baking soda",
    "black pepper",
    "butter",
    "egg",
    "flour",
    "oil",
    "olive oil",
    "pepper",
    "salt",
    "sugar",
    "water",
    "white sugar",
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


def query_intent(value: str) -> QueryIntent:
    normalized = normalize_text(value)
    if any(_contains_phrase(normalized, phrase) for phrase in _ADVENTUROUS_PHRASES):
        return QueryIntent.ADVENTUROUS
    if normalized in _BROWSE_PHRASES or any(
        _contains_phrase(normalized, phrase) for phrase in _BROWSE_PHRASES if " " in phrase
    ):
        return QueryIntent.BROWSE
    return QueryIntent.SEARCH


def split_excluded_ingredients(value: str) -> tuple[str, tuple[str, ...]]:
    """Split common English, Swedish, and Spanish exclusion phrases from a query."""
    normalized = normalize_text(value)
    excluded_phrases: list[str] = []

    def remove_match(match: re.Match[str]) -> str:
        excluded_phrases.append(match.group("items"))
        return " "

    positive = _NEGATION_PATTERN.sub(remove_match, normalized)

    def remove_short_match(match: re.Match[str]) -> str:
        items = match.group("items")
        # These are preferences rather than dependable ingredient exclusions.
        if items.split()[0] in {"quick", "fast", "spicy", "starkt", "picante"}:
            return " "
        excluded_phrases.append(items)
        return " "

    positive = _SHORT_NEGATION_PATTERN.sub(remove_short_match, positive)
    return positive, query_ingredients(excluded_phrases)


def distinctive_ingredient_terms(value: str) -> frozenset[str]:
    """Return corpus-frequency terms suitable for a bounded discovery signal."""
    return frozenset(
        term
        for term in ingredient_terms(value)
        if " " not in term
        and len(term) > 2
        and term not in _DISTINCTIVE_NOISE
        and term not in _PANTRY_STAPLES
    )


def _contains_phrase(normalized: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(normalize_text(phrase))}(?!\w)", normalized) is not None


def preference_terms(value: str) -> tuple[str, ...]:
    normalized = normalize_text(value)
    found: list[str] = []
    mappings = {
        "spicy": ("spicy", "starkt", "picante"),
        "quick": ("quick", "fast", "snabbt", "rapido", "rápido"),
        "vegetarian": ("vegetarian", "vegetarisk", "vegetariano", "vegetariana"),
        "comfort food": ("comfort food", "comfort", "husmanskost"),
    }
    for canonical, aliases in mappings.items():
        present = any(_contains_phrase(normalized, alias) for alias in aliases)
        negated = any(
            _contains_phrase(normalized, f"{negation} {alias}")
            for alias in aliases
            for negation in (
                "not",
                "no",
                "inte",
                "without",
                "avoid",
                "excluding",
                "utan",
                "sin",
            )
        )
        if present and not negated:
            found.append(canonical)
    return tuple(found)


def excluded_preference_terms(value: str) -> tuple[str, ...]:
    normalized = normalize_text(value)
    mappings = {
        "spicy": ("spicy", "starkt", "picante"),
        "quick": ("quick", "fast", "snabbt", "rapido", "rápido"),
    }
    return tuple(
        canonical
        for canonical, aliases in mappings.items()
        if any(
            _contains_phrase(normalized, f"{negation} {alias}")
            for alias in aliases
            for negation in (
                "not",
                "no",
                "inte",
                "without",
                "avoid",
                "excluding",
                "utan",
                "sin",
            )
        )
    )
