"""
Cook-path recommendation endpoint: given a macro budget, asks the local
LLM to generate a recipe from the user's actual pantry, then returns it
with deterministically-computed macros (see app/core/recipe_generation.py
for why the macro math is never trusted from the LLM itself). Includes
an accept endpoint that recomputes macros the same way and deducts the
used quantities from the pantry.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.budget_split import MacroBudget
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ollama_client import OllamaError
from app.core.recipe_generation import (
    generate_recipe,
    compute_scaled_macros,
    PantryItemInput,
    RecipeGenerationError,
)
from app.models.food_log import FoodLog, FoodLogSource
from app.models.pantry_item import PantryItem
from app.models.user import User
from app.schemas.cook import CookRecommendationRequest, CookRecommendationOut, AcceptCookRequest
from app.schemas.food_log import FoodLogOut

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _load_pantry_inputs(db: Session, current_user: User) -> tuple[list, dict]:
    pantry_rows = db.query(PantryItem).filter(PantryItem.user_id == current_user.id).all()
    pantry_items = [
        PantryItemInput(
            id=str(row.id),
            name=row.name,
            quantity=row.quantity,
            unit=row.unit,
            protein=row.protein,
            carb=row.carb,
            fat=row.fat,
            cal=row.cal,
        )
        for row in pantry_rows
    ]
    rows_by_id = {str(row.id): row for row in pantry_rows}
    return pantry_items, rows_by_id


@router.post("/cook", response_model=CookRecommendationOut)
def recommend_cook(
    payload: CookRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pantry_items, _ = _load_pantry_inputs(db, current_user)
    if not pantry_items:
        raise HTTPException(status_code=400, detail="Your pantry is empty - add some items first.")

    target = MacroBudget(protein=payload.protein, carb=payload.carb, fat=payload.fat, cal=payload.cal)

    try:
        recipe = generate_recipe(pantry_items, target)
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RecipeGenerationError as e:
        raise HTTPException(status_code=422, detail=f"Could not generate a valid recipe: {e}")

    return CookRecommendationOut(**recipe.dict())


@router.post("/cook/accept", response_model=FoodLogOut, status_code=201)
def accept_cook_recommendation(
    payload: AcceptCookRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pantry_items, rows_by_id = _load_pantry_inputs(db, current_user)
    pantry_by_id = {item.id: item for item in pantry_items}

    if not payload.ingredients_used:
        raise HTTPException(status_code=422, detail="No ingredients provided")

    total = MacroBudget(protein=0, carb=0, fat=0, cal=0)
    rows_to_update = []  # (row, new_quantity) pairs, applied only after all validation passes

    for ingredient in payload.ingredients_used:
        if ingredient.pantry_item_id not in pantry_by_id:
            raise HTTPException(
                status_code=404,
                detail=f"Pantry item '{ingredient.pantry_item_id}' not found in your pantry",
            )

        pantry_item = pantry_by_id[ingredient.pantry_item_id]
        try:
            scaled = compute_scaled_macros(pantry_item, ingredient.quantity_used)
        except RecipeGenerationError as e:
            raise HTTPException(status_code=422, detail=str(e))

        total = MacroBudget(
            protein=total.protein + scaled.protein,
            carb=total.carb + scaled.carb,
            fat=total.fat + scaled.fat,
            cal=total.cal + scaled.cal,
        )

        row = rows_by_id[ingredient.pantry_item_id]
        rows_to_update.append((row, row.quantity - ingredient.quantity_used))

    # Only mutate the pantry once every ingredient has validated successfully -
    # avoids partially deducting quantities if a later ingredient fails.
    for row, new_quantity in rows_to_update:
        row.quantity = new_quantity

    entry = FoodLog(
        user_id=current_user.id,
        source=FoodLogSource.RECOMMENDED,
        name=payload.recipe_name,
        protein=round(total.protein, 2),
        carb=round(total.carb, 2),
        fat=round(total.fat, 2),
        cal=round(total.cal, 2),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
