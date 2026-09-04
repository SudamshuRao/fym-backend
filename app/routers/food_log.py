"""
Food Log endpoints: manual entries, today's list (respecting the user's
day-rollover window), revert (soft-delete any of today's entries, not
just the most recent), and the derived Remaining calculation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.day_rollover import get_logical_day_bounds
from app.core.deps import get_current_user
from app.core.remaining import calculate_remaining
from app.models.food_log import FoodLog
from app.models.user import User
from app.schemas.food_log import FoodLogCreate, FoodLogOut, RemainingOut

router = APIRouter(prefix="/food-log", tags=["food-log"])


@router.post("", response_model=FoodLogOut, status_code=201)
def create_food_log_entry(
    payload: FoodLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = FoodLog(user_id=current_user.id, **payload.dict())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/today", response_model=list[FoodLogOut])
def get_todays_entries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns ALL of today's entries, including reverted ones, so the
    client can show a strikethrough/history view rather than entries
    just vanishing. Filter client-side on `reverted` if only active
    entries are needed.
    """
    window_start, window_end = get_logical_day_bounds(current_user.day_start_time)

    entries = (
        db.query(FoodLog)
        .filter(
            FoodLog.user_id == current_user.id,
            FoodLog.timestamp >= window_start,
            FoodLog.timestamp < window_end,
        )
        .order_by(FoodLog.timestamp.desc())
        .all()
    )
    return entries


@router.post("/{entry_id}/revert", response_model=FoodLogOut)
def revert_food_log_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reverts ANY of today's entries, not just the most recent - a user
    should be able to undo an earlier mistake without having to revert
    everything logged after it too.
    """
    entry = (
        db.query(FoodLog)
        .filter(FoodLog.id == entry_id, FoodLog.user_id == current_user.id)
        .first()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Food log entry not found")

    window_start, window_end = get_logical_day_bounds(current_user.day_start_time)
    if not (window_start <= entry.timestamp < window_end):
        raise HTTPException(status_code=400, detail="Can only revert entries from today")

    if entry.reverted:
        raise HTTPException(status_code=400, detail="Entry is already reverted")

    entry.reverted = True
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/remaining", response_model=RemainingOut)
def get_remaining(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = calculate_remaining(db, current_user)
    if result is None:
        raise HTTPException(status_code=404, detail="No daily target set yet")
    return result
