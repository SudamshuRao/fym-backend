"""
PantryItem: user's available ingredients for the cook-path recommendation
engine. Manual entry for now; barcode-scan is a Phase 5 input method that
writes to this same table, not a separate one.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)
    barcode = Column(String, nullable=True, index=True)  # populated when added via barcode scan

    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)  # e.g. "g", "oz", "count"

    # Macros for the pantry item (per the stated quantity/unit above),
    # so the cook-path scorer can use them directly without a lookup.
    protein = Column(Float, nullable=True)
    carb = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    cal = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
