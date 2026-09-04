"""
RestaurantNutrition: cached menu item nutrition data, shared across all
users (not user-scoped - this is reference data, not personal data).
Populated by the scraper pipeline (scrape_nutrition.py / eval_nutrition.py)
and refreshed periodically (target: every 30-90 days, see Phase 5's
refresh pipeline).

`restaurant_id` is a stable slug (e.g. "mcdonalds", "chipotle-mexican-grill")
so the eat-out recommendation flow can group/query by restaurant without
relying on exact name matching.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class RestaurantNutrition(Base):
    __tablename__ = "restaurant_nutrition"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    restaurant_id = Column(String, nullable=False, index=True)  # stable slug
    name = Column(String, nullable=False)  # display name, e.g. "McDonald's"
    location = Column(String, nullable=True)  # reserved for per-location data later; null = chain-wide

    menu_item = Column(String, nullable=False)
    protein = Column(Float, nullable=True)
    carb = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    cal = Column(Float, nullable=True)

    # Keyword-derived tags for the clarification-filter step (Phase 3),
    # e.g. ["spicy", "fried"]. Populated at scrape/label time, not at
    # request time - see the keyword->tag lookup table design.
    attribute_tags = Column(ARRAY(String), nullable=False, default=list)

    source_url = Column(String, nullable=True)
    last_fetched = Column(DateTime, default=datetime.utcnow, nullable=False)

    # "ok_structured" | "ok_raw" | "no_data" - mirrors scrape_nutrition.py's
    # status field, kept here so the app can tell how the data was sourced.
    status = Column(String, nullable=False, default="ok_structured")
