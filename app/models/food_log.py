"""
FoodLog: every entry the user has logged, either typed manually or
auto-created when a recommendation is accepted. `reverted` supports
Mode A's "undo last entry" requirement without deleting history outright.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class FoodLogSource(str, enum.Enum):
    LOGGED = "logged"
    RECOMMENDED = "recommended"


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    source = Column(Enum(FoodLogSource), nullable=False)
    name = Column(String, nullable=False)

    protein = Column(Float, nullable=False)
    carb = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)
    cal = Column(Float, nullable=False)

    # Real wall-clock time the entry was logged. Which "day" this belongs
    # to is derived at query time via the user's day_start_time, not
    # stored redundantly here - see app/core/day_rollover.py.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Soft-delete flag for the revert feature - keeps the row (and history)
    # rather than hard-deleting it.
    reverted = Column(Boolean, default=False, nullable=False)
