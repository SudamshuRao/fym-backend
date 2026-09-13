"""
Import every model here so Base.metadata (and Alembic's autogenerate)
picks up all tables, even though nothing in this file is used directly.
"""

from app.models.user import User
from app.models.daily_target import DailyTarget
from app.models.food_log import FoodLog, FoodLogSource
from app.models.pantry_item import PantryItem
from app.models.preference_summary import PreferenceSummary
from app.models.restaurant_nutrition import RestaurantNutrition
from app.models.recommendation_event import RecommendationEvent, RecommendationType

__all__ = [
    "User",
    "DailyTarget",
    "FoodLog",
    "FoodLogSource",
    "PantryItem",
    "PreferenceSummary",
    "RestaurantNutrition",
    "RecommendationEvent",
    "RecommendationType",
]
