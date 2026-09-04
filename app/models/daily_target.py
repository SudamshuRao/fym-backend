"""
DailyTarget: set once, persists until the user explicitly updates it.
One row per user (not per day) - "today's target" is just whatever the
current row says.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DailyTarget(Base):
    __tablename__ = "daily_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    protein = Column(Float, nullable=False)
    carb = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)
    cal = Column(Float, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
