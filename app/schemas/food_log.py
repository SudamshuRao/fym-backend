from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.food_log import FoodLogSource


class FoodLogCreate(BaseModel):
    name: str
    protein: float
    carb: float
    fat: float
    cal: float
    source: FoodLogSource = FoodLogSource.LOGGED


class FoodLogOut(BaseModel):
    id: UUID
    name: str
    source: FoodLogSource
    protein: float
    carb: float
    fat: float
    cal: float
    timestamp: datetime
    reverted: bool

    class Config:
        from_attributes = True


class RemainingOut(BaseModel):
    """
    Derived, not stored: Daily Target minus the sum of today's
    non-reverted Food Log entries, where "today" is the user's current
    logical-day window (see app/core/day_rollover.py).
    """
    protein: float
    carb: float
    fat: float
    cal: float
    # Echoed back so the client can show "X of Y" without a second call.
    target_protein: float
    target_carb: float
    target_fat: float
    target_cal: float
