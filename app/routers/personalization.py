"""
Personalization endpoints. The "periodic" job is manually triggerable
here rather than actually scheduled - real scheduling infrastructure
(cron, background workers) is a Phase 5 concern, same as the nutrition
data refresh pipeline was deferred earlier. This gives the same
underlying logic something to be triggered by later.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ollama_client import OllamaError
from app.core.personalization import generate_summary, PersonalizationError
from app.models.preference_summary import PreferenceSummary
from app.models.recommendation_event import RecommendationEvent
from app.models.user import User
from app.schemas.personalization import PreferenceSummaryOut, PersonalizationRefreshOut

router = APIRouter(prefix="/personalization", tags=["personalization"])


@router.get("/summary", response_model=PreferenceSummaryOut)
def get_preference_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(PreferenceSummary).filter(PreferenceSummary.user_id == current_user.id).first()
    if row is None:
        return PreferenceSummaryOut(prefers=[], avoids=[])
    return PreferenceSummaryOut(**row.summary)


@router.post("/refresh", response_model=PersonalizationRefreshOut)
def refresh_preference_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(PreferenceSummary).filter(PreferenceSummary.user_id == current_user.id).first()
    current_summary = row.summary if row else {}

    recent_events = (
        db.query(RecommendationEvent)
        .filter(RecommendationEvent.user_id == current_user.id)
        .all()
    )

    try:
        new_summary = generate_summary(current_summary, recent_events)
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except PersonalizationError as e:
        raise HTTPException(status_code=422, detail=f"Could not generate summary: {e}")

    if row is None:
        row = PreferenceSummary(user_id=current_user.id, summary=new_summary)
        db.add(row)
    else:
        row.summary = new_summary

    events_count = len(recent_events)
    # The recent window is folded into the summary above and doesn't
    # need to be kept afterward - matches the "running summary, not raw
    # history" decision from planning.
    for event in recent_events:
        db.delete(event)

    db.commit()

    return PersonalizationRefreshOut(
        summary=PreferenceSummaryOut(**new_summary),
        events_processed=events_count,
    )
