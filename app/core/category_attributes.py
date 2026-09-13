"""
Two small, hand-maintained lookup tables driving the eat-out
clarification flow. Both are deterministic - no LLM involved, since the
answer space for "what attributes matter for a burger" is small and
known in advance. Grows slowly over time as more categories/keywords are
added; not meant to be exhaustive on day one.
"""

from __future__ import annotations


# category -> list of clarifying attributes shown as tappable options
# when a request is broad (e.g. "I want a burger" with nothing else
# specified). Each attribute has a UI key and its possible values.
CATEGORY_ATTRIBUTES: dict[str, list[dict]] = {
    "burger": [
        {"key": "spice_level", "label": "Spice level", "options": ["mild", "spicy", "either"]},
        {"key": "cooking_style", "label": "Style", "options": ["fried", "grilled", "either"]},
    ],
    "chicken": [
        {"key": "spice_level", "label": "Spice level", "options": ["mild", "spicy", "either"]},
        {"key": "cooking_style", "label": "Style", "options": ["fried", "grilled", "either"]},
    ],
    "ice_cream": [
        {"key": "format", "label": "Format", "options": ["cone", "cup", "shake", "either"]},
    ],
    "taco": [
        {"key": "protein", "label": "Protein", "options": ["chicken", "beef", "steak", "plant-based", "either"]},
        {"key": "spice_level", "label": "Spice level", "options": ["mild", "spicy", "either"]},
    ],
    "salad": [
        {"key": "protein", "label": "Protein", "options": ["chicken", "steak", "plant-based", "either"]},
    ],
    "coffee": [
        {"key": "temperature", "label": "Temperature", "options": ["hot", "iced", "either"]},
    ],
}


# keyword found in a menu item's name (case-insensitive substring match)
# -> the attribute tag it implies. Applied once at scrape/load time, not
# per-request - see app/scripts/load_restaurant_nutrition.py.
KEYWORD_TAG_MAP: dict[str, str] = {
    "spicy": "spicy",
    "hot": "spicy",
    "diablo": "spicy",
    "buffalo": "spicy",
    "ghost pepper": "spicy",
    "grilled": "grilled",
    "crispy": "fried",
    "fried": "fried",
    "iced": "iced",
    "frozen": "iced",
    "cone": "cone",
    "cup": "cup",
    "shake": "shake",
    "milkshake": "shake",
    "chicken": "chicken",
    "beef": "beef",
    "steak": "steak",
    "veggie": "plant-based",
    "vegetarian": "plant-based",
    "plant based": "plant-based",
    "plant-based": "plant-based",
}


def derive_tags_from_name(menu_item_name: str) -> list[str]:
    """
    Scans a menu item's name for known keywords and returns the implied
    tags, deduplicated. Deterministic - same input always gives the same
    output, no LLM involved.
    """
    name_lower = menu_item_name.lower()
    tags = set()
    for keyword, tag in KEYWORD_TAG_MAP.items():
        if keyword in name_lower:
            tags.add(tag)
    return sorted(tags)
