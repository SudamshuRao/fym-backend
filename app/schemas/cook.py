from pydantic import BaseModel


class CookRecommendationRequest(BaseModel):
    protein: float
    carb: float
    fat: float
    cal: float


class RecipeIngredientOut(BaseModel):
    pantry_item_id: str
    name: str
    quantity_used: float
    unit: str


class CookRecommendationOut(BaseModel):
    recipe_name: str
    steps: list[str]
    ingredients_used: list[RecipeIngredientOut]
    protein: float
    carb: float
    fat: float
    cal: float
    fit_score: float


class AcceptCookIngredient(BaseModel):
    pantry_item_id: str
    quantity_used: float


class AcceptCookRequest(BaseModel):
    """
    Deliberately does NOT accept macro totals from the client - only the
    recipe name and which pantry items/quantities were used. Macros are
    always recomputed server-side from the pantry's own known values,
    same as at generation time.
    """
    recipe_name: str
    ingredients_used: list[AcceptCookIngredient]
