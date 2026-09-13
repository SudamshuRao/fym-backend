from typing import Optional

from pydantic import BaseModel


class EatOutRecommendationRequest(BaseModel):
    protein: float
    carb: float
    fat: float
    cal: float
    restaurant_id: Optional[str] = None  # filter to one restaurant if provided
    limit: int = 10
    # If lat/lon are provided, results are restricted to chains with a
    # real-world location within radius_km - overrides restaurant_id.
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: float = 5.0


class RecommendedItem(BaseModel):
    restaurant_id: str
    restaurant_name: str
    menu_item: str
    protein: Optional[float]
    carb: Optional[float]
    fat: Optional[float]
    cal: Optional[float]
    fit_score: float  # lower is better; 0 = exact match
    restaurant_nutrition_id: str  # needed to accept this specific item
    distance_km: Optional[float] = None  # only populated when lat/lon were provided


class EatOutRecommendationOut(BaseModel):
    results: list[RecommendedItem]


class AcceptEatOutRequest(BaseModel):
    restaurant_nutrition_id: str
