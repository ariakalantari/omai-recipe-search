from __future__ import annotations

import re

from recipe_search.domain import Recipe
from recipe_search.normalization import canonicalize_known_foods, normalize_text

_PARENTHETICAL = re.compile(r"\([^)]*\)")
_LEADING_AMOUNT = re.compile(r"^(?:\d+(?:[./]\d+)?|\d+\s+\d+/\d+|one|two|three|four|five|six)\s+")

_LABEL_SKIP = {
    "all-natural",
    "and",
    "about",
    "advertisement",
    "beaten",
    "boneless",
    "chopped",
    "condensed",
    "crushed",
    "diced",
    "divided",
    "filtered",
    "finely",
    "for",
    "fresh",
    "frying",
    "ground",
    "in",
    "large",
    "lightly",
    "medium",
    "minus",
    "minced",
    "optional",
    "outer",
    "peeled",
    "plus",
    "roughly",
    "slice",
    "slices",
    "skinless",
    "sliced",
    "small",
    "tender",
    "thin",
    "to",
    "tough",
    "portion",
    "removed",
    "only",
    "recipe",
    "still",
    "store-bought",
    "superfine",
    "unsweetened",
    "bottled",
    "cleaned",
    "creamy",
    "fat",
    "fat-free",
    "frozen",
    "granulated",
    "natural",
    "packed",
    "reduced",
    "reserving",
    "rinsed",
    "room",
    "spray",
    "sweetened",
    "temperature",
    "thawed",
    "thinly",
    "top",
    "un-iced",
    "whipped",
    "aisle",
    "bought",
    "canister",
    "coarsely",
    "cold",
    "cooked",
    "cooking",
    "cubed",
    "cut",
    "dairy",
    "drained",
    "fine",
    "frosted",
    "grain",
    "halves",
    "including",
    "into",
    "long",
    "mix",
    "quick",
    "sea",
    "store",
    "shredded",
    "the",
    "uncooked",
    "unfrosted",
    "unsliced",
}

_LEADING_UNITS = {
    "bag",
    "bags",
    "bottle",
    "bottles",
    "box",
    "boxes",
    "can",
    "cans",
    "clove",
    "cloves",
    "container",
    "containers",
    "cup",
    "cups",
    "cube",
    "cubes",
    "gram",
    "grams",
    "g",
    "kg",
    "jigger",
    "jiggers",
    "lb",
    "lbs",
    "loaf",
    "loaves",
    "ounce",
    "ounces",
    "oz",
    "package",
    "packages",
    "piece",
    "pieces",
    "pound",
    "pounds",
    "slice",
    "slices",
    "tablespoon",
    "tablespoons",
    "tbsp",
    "teaspoon",
    "teaspoons",
    "tsp",
}

_PANTRY_LABELS = {
    "all purpose flour",
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

_PANTRY_WORDS = {
    "baking",
    "black",
    "butter",
    "egg",
    "eggs",
    "flour",
    "oil",
    "pepper",
    "powder",
    "salt",
    "soda",
    "sugar",
    "vegetable",
    "water",
    "white",
}

_CLAUSE_WORDS = {
    "following",
    "from",
    "garnish",
    "instructions",
    "near",
    "recommended",
    "stocked",
    "substitute",
}

_FEATURE_PENALTIES = {
    "agave",
    "bay",
    "color",
    "frosting",
    "garnish",
    "honey",
    "leaf",
    "leaves",
    "oil",
    "sauce",
    "seasoning",
    "syrup",
}

_DISH_KINDS = (
    ("stir fry", "stir-fry"),
    ("mac and cheese", "mac and cheese dish"),
    ("ice cream", "frozen dessert"),
    ("gelato", "frozen dessert"),
    ("croquembouche", "pastry"),
    ("truffle", "bite-sized treat"),
    ("pudding", "dessert"),
    ("slaw", "salad"),
    ("rangoon", "filled wonton"),
    ("dumpling", "dumpling dish"),
    ("meatloaf", "meatloaf"),
    ("casserole", "casserole"),
    ("sandwich", "sandwich"),
    ("pancake", "pancake dish"),
    ("cupcake", "cupcake"),
    ("brownie", "brownie"),
    ("cookie", "cookie"),
    ("biscuit", "biscuit"),
    ("muffin", "muffin"),
    ("noodle", "noodle dish"),
    ("pasta", "pasta dish"),
    ("spaghetti", "pasta dish"),
    ("lasagna", "lasagna"),
    ("salad", "salad"),
    ("curry", "curry"),
    ("soup", "soup"),
    ("stew", "stew"),
    ("chili", "chili"),
    ("taco", "taco dish"),
    ("pizza", "pizza"),
    ("burger", "burger"),
    ("bread", "bread"),
    ("cake", "cake"),
    ("pie", "pie"),
    ("roast", "roast"),
)

_STYLE_WORDS = (
    ("slow cooker", "slow-cooked"),
    ("slow cooked", "slow-cooked"),
    ("grilled", "grilled"),
    ("roasted", "roasted"),
    ("baked", "baked"),
    ("creamy", "creamy"),
    ("spicy", "spicy"),
    ("crispy", "crispy"),
    ("stuffed", "stuffed"),
)


def _ingredient_label(line: str) -> str | None:
    first_word = normalize_text(line).split()[:1]
    if line.rstrip().endswith(":") or first_word in [["if"], ["or"], ["store-bought"]]:
        return None
    text = canonicalize_known_foods(_PARENTHETICAL.sub(" ", line))
    text = _LEADING_AMOUNT.sub("", text)
    words: list[str] = []
    for word in text.replace(",", " ").split():
        if word in _CLAUSE_WORDS:
            break
        if word in _LABEL_SKIP or word in _LEADING_UNITS or word[0].isdigit():
            continue
        if words and word == words[-1]:
            continue
        words.append(word)
    while words and words[0] in {"and", "or"}:
        words.pop(0)
    while words and words[-1] in {"and", "or"}:
        words.pop()
    if not words:
        return None
    words = words[:5]
    while words and words[-1] in {"and", "or"}:
        words.pop()
    label = " ".join(words).strip(" -")
    normalized_label = normalize_text(label)
    content_words = set(normalized_label.split()) - {"and", "or"}
    if (
        not label
        or normalized_label in _PANTRY_LABELS
        or (content_words and content_words.issubset(_PANTRY_WORDS))
    ):
        return None
    return label


def _features(recipe: Recipe, limit: int = 3) -> list[str]:
    candidates: list[tuple[float, int, str]] = []
    seen: set[str] = set()
    title_terms = set(normalize_text(recipe.name).replace("-", " ").split())
    for index, line in enumerate(recipe.ingredients):
        label = _ingredient_label(line)
        normalized = normalize_text(label or "")
        if not label or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        label_terms = set(normalized.replace("-", " ").split()) - {"and", "or"}
        score = 1.0 - min(index, 20) * 0.025
        score += 2.0 * len(title_terms.intersection(label_terms))
        score -= 0.6 * len(_FEATURE_PENALTIES.intersection(label_terms))
        candidates.append((score, index, label))
    selected = sorted(candidates, key=lambda item: (-item[0], item[1]))[:limit]
    return [label for _, _, label in selected]


def _join_features(features: list[str]) -> str:
    if len(features) == 1:
        return features[0]
    if len(features) == 2:
        return f"{features[0]} and {features[1]}"
    return f"{', '.join(features[:-1])}, and {features[-1]}"


def recipe_summary(recipe: Recipe) -> str:
    """Build a short factual summary without treating a method step as description."""
    if recipe.description:
        return recipe.description

    normalized_title = normalize_text(recipe.name)
    style = next(
        (label for phrase, label in _STYLE_WORDS if phrase in normalized_title),
        None,
    )
    kind = next(
        (label for phrase, label in _DISH_KINDS if phrase in normalized_title),
        "recipe",
    )
    noun = f"{style} {kind}" if style and not kind.startswith(style) else kind
    features = _features(recipe)
    if features:
        return f"A {noun} featuring {_join_features(features)}."
    return f"A {noun} from the recipe collection."
