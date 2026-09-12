from typing import Optional

from pydantic import BaseModel


class EatOutRecommendationRequest(BaseModel):
    protein: float
    carb: float
    fat: float
    cal: float
    restaurant_id: Optional[str] = None  # filter to one restaurant if provided
    limit: int = 10


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


class EatOutRecommendationOut(BaseModel):
    results: list[RecommendedItem]


class AcceptEatOutRequest(BaseModel):
    restaurant_nutrition_id: str
