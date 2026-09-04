"""
User model. Single-user today, but every other table is keyed by user_id
from day one so auth/multi-tenancy can be turned on later without a
schema rewrite.
"""

import uuid
from datetime import datetime, time

from sqlalchemy import Column, String, DateTime, Time
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Day-rollover setting: defines the logical-day boundary for this user.
    # Default midnight; user can change it (e.g. 04:00 for late-night eaters).
    day_start_time = Column(Time, nullable=False, default=time(0, 0))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
