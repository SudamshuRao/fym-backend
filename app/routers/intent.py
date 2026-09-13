"""
Free-text intent parsing endpoint. Parses the request via LLM, then
looks up (deterministically) whether that category has any clarifying
attributes to show - and only includes them if the request was actually
broad and those attributes weren't already mentioned.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.category_attributes import CATEGORY_ATTRIBUTES
from app.core.deps import get_current_user
from app.core.intent_parsing import parse_intent, IntentParseError
from app.core.ollama_client import OllamaError
from app.models.user import User
from app.schemas.intent import IntentParseRequest, IntentParseOut, ClarificationAttribute

router = APIRouter(prefix="/intent", tags=["intent"])


@router.post("/parse", response_model=IntentParseOut)
def parse_food_intent(
    payload: IntentParseRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = parse_intent(payload.text)
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except IntentParseError as e:
        raise HTTPException(status_code=422, detail=f"Could not parse intent: {e}")

    clarification_options = []
    if result.is_broad:
        attributes = CATEGORY_ATTRIBUTES.get(result.category, [])
        # Only ask about attributes the user hasn't already specified.
        clarification_options = [
            ClarificationAttribute(**attr)
            for attr in attributes
            if attr["key"] not in result.mentioned_attributes
        ]

    return IntentParseOut(
        category=result.category,
        is_broad=result.is_broad,
        mentioned_attributes=result.mentioned_attributes,
        clarification_options=clarification_options,
    )
