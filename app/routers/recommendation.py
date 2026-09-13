"""
Eat-out recommendation endpoint: given a macro budget, scores every
cached restaurant menu item against it and returns the best fits.
Includes an accept endpoint that logs the chosen item using its macros
looked up fresh from the database - never trusting whatever the client
might send, consistent with how the rest of this app treats macro data.

Optionally filters by real-world location: if lat/lon are provided,
only chains with an actual nearby location (via free OpenStreetMap
Overpass lookup) are considered - overriding a plain restaurant_id
filter, since "what's actually near me" is more useful than "search
this one chain everywhere."
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.budget_split import MacroBudget
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.macro_fit import score_fit, apply_preference_weighting
from app.core.overpass_client import find_nearby_chains, OverpassError
from app.models.food_log import FoodLog, FoodLogSource
from app.models.preference_summary import PreferenceSummary
from app.models.recommendation_event import RecommendationEvent, RecommendationType
from app.models.restaurant_nutrition import RestaurantNutrition
from app.models.user import User
from app.schemas.food_log import FoodLogOut
from app.schemas.personalization import SkipEatOutRequest
from app.schemas.recommendation import (
    EatOutRecommendationRequest,
    EatOutRecommendationOut,
    RecommendedItem,
    AcceptEatOutRequest,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/eat-out", response_model=EatOutRecommendationOut)
def recommend_eat_out(
    payload: EatOutRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(RestaurantNutrition).filter(RestaurantNutrition.status == "ok_structured")

    distance_by_restaurant_id = {}

    if payload.lat is not None and payload.lon is not None:
        # Location overrides a plain restaurant_id filter - "what's near
        # me" is more useful than "search one specific chain everywhere."
        known_chains = (
            db.query(RestaurantNutrition.restaurant_id, RestaurantNutrition.name)
            .distinct()
            .all()
        )
        try:
            nearby = find_nearby_chains(payload.lat, payload.lon, payload.radius_km, known_chains)
        except OverpassError as e:
            raise HTTPException(status_code=503, detail=str(e))

        if not nearby:
            return EatOutRecommendationOut(results=[])

        nearby_ids = [r["restaurant_id"] for r in nearby]
        distance_by_restaurant_id = {r["restaurant_id"]: r["distance_km"] for r in nearby}
        query = query.filter(RestaurantNutrition.restaurant_id.in_(nearby_ids))
    elif payload.restaurant_id:
        query = query.filter(RestaurantNutrition.restaurant_id == payload.restaurant_id)

    items = query.all()

    # Only score items with complete macro data - can't fairly rank
    # something missing a protein/carb/fat value against a full budget.
    scorable_items = [item for item in items if None not in (item.protein, item.carb, item.fat, item.cal)]

    target = MacroBudget(protein=payload.protein, carb=payload.carb, fat=payload.fat, cal=payload.cal)

    # Fetch the user's preference summary once (soft weighting, never a
    # hard filter - and completely absent for new users, which is fine).
    pref_row = db.query(PreferenceSummary).filter(PreferenceSummary.user_id == current_user.id).first()
    preference_summary = pref_row.summary if pref_row else None

    scored = []
    for item in scorable_items:
        macros = MacroBudget(protein=item.protein, carb=item.carb, fat=item.fat, cal=item.cal)
        base_score = score_fit(macros, target)
        adjusted_score = apply_preference_weighting(item.menu_item, base_score, preference_summary)
        scored.append((item, macros, adjusted_score))

    scored.sort(key=lambda triple: triple[2])
    scored = scored[: payload.limit]

    results = [
        RecommendedItem(
            restaurant_id=item.restaurant_id,
            restaurant_name=item.name,
            menu_item=item.menu_item,
            protein=macros.protein,
            carb=macros.carb,
            fat=macros.fat,
            cal=macros.cal,
            fit_score=round(score, 4),
            restaurant_nutrition_id=str(item.id),
            distance_km=distance_by_restaurant_id.get(item.restaurant_id),
        )
        for item, macros, score in scored
    ]

    return EatOutRecommendationOut(results=results)


@router.post("/eat-out/accept", response_model=FoodLogOut, status_code=201)
def accept_eat_out_recommendation(
    payload: AcceptEatOutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(RestaurantNutrition)
        .filter(RestaurantNutrition.id == payload.restaurant_nutrition_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    if None in (item.protein, item.carb, item.fat, item.cal):
        raise HTTPException(status_code=422, detail="This menu item is missing macro data and can't be logged")

    entry = FoodLog(
        user_id=current_user.id,
        source=FoodLogSource.RECOMMENDED,
        name=f"{item.name}: {item.menu_item}",
        protein=item.protein,
        carb=item.carb,
        fat=item.fat,
        cal=item.cal,
    )
    db.add(entry)

    db.add(RecommendationEvent(
        user_id=current_user.id,
        recommendation_type=RecommendationType.EAT_OUT,
        identifier=item.menu_item,
        accepted=True,
    ))

    db.commit()
    db.refresh(entry)
    return entry


@router.post("/eat-out/skip", status_code=204)
def skip_eat_out_recommendation(
    payload: SkipEatOutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.add(RecommendationEvent(
        user_id=current_user.id,
        recommendation_type=RecommendationType.EAT_OUT,
        identifier=payload.menu_item,
        accepted=False,
    ))
    db.commit()
    return None
