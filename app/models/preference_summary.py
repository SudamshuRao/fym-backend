"""
PreferenceSummary: one row per user, holding a JSON blob of soft
personalization preferences derived from accept/skip behavior. This is a
RUNNING SUMMARY, not raw history - the periodic personalization job
(Phase 4) replaces this row's content wholesale on each run rather than
appending to it, per the privacy/storage decision made during planning.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class PreferenceSummary(Base):
    __tablename__ = "preference_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Free-form JSON, e.g.:
    # {"prefers": ["chicken", "high-protein breakfasts"], "avoids": ["salads at dinner"]}
    # Shape is intentionally flexible since the summarization prompt may evolve.
    summary = Column(JSONB, nullable=False, default=dict)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
