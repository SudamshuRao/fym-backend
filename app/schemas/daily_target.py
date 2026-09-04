from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DailyTargetSet(BaseModel):
    """Used for both create and update - it's the same operation (upsert)."""
    protein: float
    carb: float
    fat: float
    cal: float


class DailyTargetOut(BaseModel):
    id: UUID
    protein: float
    carb: float
    fat: float
    cal: float
    updated_at: datetime

    class Config:
        from_attributes = True
