"""
RecommendationEvent: a lightweight accept/skip signal for a shown
recommendation - NOT the permanent raw history that was explicitly
decided against during planning. This table is meant to be short-lived:
the periodic personalization job (Phase 4) reads recent events, folds
them into the user's PreferenceSummary, and deletes them - so this
table only ever holds "since the last summarization run," not the
user's whole history.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class RecommendationType(str, enum.Enum):
    EAT_OUT = "eat_out"
    COOK = "cook"


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    recommendation_type = Column(Enum(RecommendationType), nullable=False)
    identifier = Column(String, nullable=False)  # menu item name or recipe name
    accepted = Column(Boolean, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
