"""
Free-text intent parsing: turns something like "I want a burger" into
structured category tags, a signal for whether the request is broad or
already specific, and any attributes the user already mentioned (e.g.
"spicy fried chicken sandwich" is specific enough to skip clarification
entirely).

This is the genuinely open-ended piece of the eat-out flow - unlike
category->attribute lookups or keyword tagging (both deterministic),
there's no fixed answer space for "what did the user mean by this
sentence." That's exactly the kind of task the LLM is scoped for in
this app.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.category_attributes import CATEGORY_ATTRIBUTES
from app.core.ollama_client import call_ollama, parse_json_response


class IntentParseError(Exception):
    pass


class ParsedIntent(BaseModel):
    category: str
    is_broad: bool
    mentioned_attributes: dict[str, str]  # e.g. {"spice_level": "spicy"}


KNOWN_CATEGORIES = sorted(CATEGORY_ATTRIBUTES.keys())


def build_intent_prompt(text: str) -> str:
    categories_list = ", ".join(KNOWN_CATEGORIES)
    return f"""Classify this food request: "{text}"

Known food categories: {categories_list}

Respond with ONLY a JSON object in this exact shape, nothing else:
{{
  "category": "<one of the known categories that best matches, or the single most obvious general category if none fit exactly>",
  "is_broad": <true if the request is vague/general like "I want a burger", false if it already specifies details like spice level, cooking style, or protein type>,
  "mentioned_attributes": {{"<attribute key>": "<value>", ...}}
}}

Only include mentioned_attributes the user actually stated - don't guess or fill in defaults."""


def parse_intent(text: str, llm_call_fn=call_ollama) -> ParsedIntent:
    prompt = build_intent_prompt(text)
    raw_response = llm_call_fn(prompt)
    parsed = parse_json_response(raw_response)

    if "category" not in parsed or "is_broad" not in parsed:
        raise IntentParseError(f"LLM response missing required fields: {parsed}")

    return ParsedIntent(
        category=parsed["category"],
        is_broad=bool(parsed["is_broad"]),
        mentioned_attributes=parsed.get("mentioned_attributes", {}) or {},
    )
