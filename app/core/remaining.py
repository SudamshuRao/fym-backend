"""
Remaining calculation: Daily Target minus the sum of today's non-reverted
Food Log entries, where "today" is computed via the day-rollover window.

This is deliberately a plain function, not tucked inside a router, so
Phase 3's recommendation engine can call it directly later without going
through HTTP - matches the "recommendation engine is decoupled from the
tracker" design decision from planning.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.day_rollover import get_logical_day_bounds
from app.models.daily_target import DailyTarget
from app.models.food_log import FoodLog
from app.models.user import User


def calculate_remaining(db: Session, user: User) -> dict:
    """
    Returns a dict with remaining protein/carb/fat/cal plus the target
    values, or None if the user hasn't set a Daily Target yet.
    """
    target = db.query(DailyTarget).filter(DailyTarget.user_id == user.id).first()
    if target is None:
        return None

    window_start, window_end = get_logical_day_bounds(user.day_start_time)

    todays_entries = (
        db.query(FoodLog)
        .filter(
            FoodLog.user_id == user.id,
            FoodLog.reverted == False,  # noqa: E712 - SQLAlchemy requires == not `is`
            FoodLog.timestamp >= window_start,
            FoodLog.timestamp < window_end,
        )
        .all()
    )

    logged_protein = sum(e.protein for e in todays_entries)
    logged_carb = sum(e.carb for e in todays_entries)
    logged_fat = sum(e.fat for e in todays_entries)
    logged_cal = sum(e.cal for e in todays_entries)

    return {
        "protein": target.protein - logged_protein,
        "carb": target.carb - logged_carb,
        "fat": target.fat - logged_fat,
        "cal": target.cal - logged_cal,
        "target_protein": target.protein,
        "target_carb": target.carb,
        "target_fat": target.fat,
        "target_cal": target.cal,
    }
