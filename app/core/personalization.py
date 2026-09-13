"""
Periodic personalization job: takes the user's current PreferenceSummary
plus recent accept/skip events, and asks a local LLM to produce an
updated summary - which REPLACES the old one wholesale, per the
"running summary, not raw history" decision made during planning.

This is the 5th LLM use case in the app, and one of the three originally
scoped in the architecture decision (alongside intent parsing and the
nutrition-extraction fallback). Free/local via Ollama, same as
everything else.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.ollama_client import call_ollama, parse_json_response
from app.models.recommendation_event import RecommendationEvent


class PersonalizationError(Exception):
    pass


class EventSummaryInput(BaseModel):
    recommendation_type: str
    identifier: str
    accepted: bool


def build_summary_prompt(current_summary: dict, recent_events: list[EventSummaryInput]) -> str:
    events_lines = "\n".join(
        f"- {'Accepted' if e.accepted else 'Skipped'} ({e.recommendation_type}): {e.identifier}"
        for e in recent_events
    )

    return f"""You are analyzing a user's food recommendation history to update their
soft preference profile.

Current preference summary:
{current_summary if current_summary else "(none yet - this is the first run)"}

Recent activity since the last update:
{events_lines if events_lines else "(no new activity)"}

Based on the current summary AND the recent activity, produce an UPDATED
summary that replaces the old one entirely (don't just append - revise
your understanding of the user's preferences).

Respond with ONLY a JSON object in this exact shape, nothing else:
{{
  "prefers": ["<short phrase>", ...],
  "avoids": ["<short phrase>", ...]
}}

Keep each list to at most 5 items. Base this only on patterns actually
visible in the activity above - don't invent preferences with no
supporting evidence. If there isn't enough activity yet to say anything
meaningful, return empty lists rather than guessing."""


def generate_summary(
    current_summary: dict,
    recent_events: list[RecommendationEvent],
    llm_call_fn=call_ollama,
) -> dict:
    event_inputs = [
        EventSummaryInput(
            recommendation_type=e.recommendation_type.value if hasattr(e.recommendation_type, "value") else e.recommendation_type,
            identifier=e.identifier,
            accepted=e.accepted,
        )
        for e in recent_events
    ]

    prompt = build_summary_prompt(current_summary, event_inputs)
    raw_response = llm_call_fn(prompt)
    parsed = parse_json_response(raw_response)

    if "prefers" not in parsed or "avoids" not in parsed:
        raise PersonalizationError(f"LLM response missing required fields: {parsed}")

    if not isinstance(parsed["prefers"], list) or not isinstance(parsed["avoids"], list):
        raise PersonalizationError(f"LLM response fields must be lists: {parsed}")

    return {
        "prefers": [str(p) for p in parsed["prefers"]][:5],
        "avoids": [str(a) for a in parsed["avoids"]][:5],
    }
