"""
Eat-out recommendation endpoint: given a macro budget, scores every
cached restaurant menu item against it and returns the best fits.

This is intentionally the simplest possible version - no location
lookup, no clarification flow, no attribute-tag filtering yet. Those
come later in Phase 3. This endpoint proves the core loop works: real
scraped data -> deterministic scoring -> ranked results.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.budget_split import MacroBudget
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.macro_fit import rank_candidates
from app.models.restaurant_nutrition import RestaurantNutrition
from app.models.user import User
from app.schemas.recommendation import (
    EatOutRecommendationRequest,
    EatOutRecommendationOut,
    RecommendedItem,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/eat-out", response_model=EatOutRecommendationOut)
def recommend_eat_out(
    payload: EatOutRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(RestaurantNutrition).filter(RestaurantNutrition.status == "ok_structured")
    if payload.restaurant_id:
        query = query.filter(RestaurantNutrition.restaurant_id == payload.restaurant_id)

    items = query.all()

    # Only score items with complete macro data - can't fairly rank
    # something missing a protein/carb/fat value against a full budget.
    candidates = [
        (str(item.id), MacroBudget(protein=item.protein, carb=item.carb, fat=item.fat, cal=item.cal))
        for item in items
        if None not in (item.protein, item.carb, item.fat, item.cal)
    ]
    items_by_id = {str(item.id): item for item in items}

    target = MacroBudget(protein=payload.protein, carb=payload.carb, fat=payload.fat, cal=payload.cal)
    ranked = rank_candidates(candidates, target, limit=payload.limit)

    results = [
        RecommendedItem(
            restaurant_id=items_by_id[item_id].restaurant_id,
            restaurant_name=items_by_id[item_id].name,
            menu_item=items_by_id[item_id].menu_item,
            protein=macros.protein,
            carb=macros.carb,
            fat=macros.fat,
            cal=macros.cal,
            fit_score=round(score, 4),
        )
        for item_id, macros, score in ranked
    ]

    return EatOutRecommendationOut(results=results)
