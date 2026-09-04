"""
Mode B (standalone quick-use) endpoints.

POST /standalone/budget      - stateless, no DB writes. User types in a
                                macro budget directly; optionally split it
                                (full/partial/N-way) using the same math
                                Mode A uses on its derived Remaining.
POST /standalone/add-to-daily - the opt-in persistence step: logs what was
                                actually eaten as a normal Food Log entry
                                (same table Mode A writes to), then
                                reports the resulting Remaining - or, if
                                no Daily Target exists, says so clearly
                                rather than silently failing.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.budget_split import split_budget, MacroBudget
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.remaining import calculate_remaining
from app.models.food_log import FoodLog, FoodLogSource
from app.models.user import User
from app.schemas.standalone import (
    StandaloneBudgetRequest,
    StandaloneBudgetOut,
    AddToDailyRequest,
    AddToDailyOut,
)

router = APIRouter(prefix="/standalone", tags=["standalone"])


@router.post("/budget", response_model=StandaloneBudgetOut)
def calculate_standalone_budget(payload: StandaloneBudgetRequest):
    """
    No auth required and no DB access - this is pure math on whatever
    the client sends. Nothing is persisted, matching Mode B's "no
    persistence" requirement.
    """
    total = MacroBudget(protein=payload.protein, carb=payload.carb, fat=payload.fat, cal=payload.cal)
    result = split_budget(total, payload.split_mode, payload.split_value)
    return StandaloneBudgetOut(**result.dict())


@router.post("/add-to-daily", response_model=AddToDailyOut)
def add_standalone_entry_to_daily(
    payload: AddToDailyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = FoodLog(
        user_id=current_user.id,
        source=FoodLogSource.LOGGED,
        name=payload.name,
        protein=payload.protein,
        carb=payload.carb,
        fat=payload.fat,
        cal=payload.cal,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    remaining = calculate_remaining(db, current_user)

    if remaining is None:
        # No Daily Target set - nothing to subtract from. Rather than
        # blocking the log or returning a 404, confirm the entry was
        # still recorded and show the raw negative usage starting from
        # zero, so the user isn't left guessing what happened.
        return AddToDailyOut(
            logged_entry_id=str(entry.id),
            has_daily_target=False,
            remaining_protein=-payload.protein,
            remaining_carb=-payload.carb,
            remaining_fat=-payload.fat,
            remaining_cal=-payload.cal,
            message=(
                "No daily target is set, so there's nothing to subtract this from. "
                "The entry was logged; values shown are your usage so far today, "
                "starting from zero."
            ),
        )

    return AddToDailyOut(
        logged_entry_id=str(entry.id),
        has_daily_target=True,
        remaining_protein=remaining["protein"],
        remaining_carb=remaining["carb"],
        remaining_fat=remaining["fat"],
        remaining_cal=remaining["cal"],
        message="Logged and subtracted from your daily target.",
    )
