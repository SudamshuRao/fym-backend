"""
Recipe generation: given the user's pantry and a macro target, asks a
local LLM (via Ollama) to pick a subset of pantry ingredients and write
a step-by-step recipe using them.

Critical design point, consistent with the rest of the app's "no LLM in
the arithmetic hot path" principle: the LLM's job is ingredient
selection and step-writing, NOT macro math. Whatever quantities the LLM
says to use, the actual protein/carb/fat/cal totals are computed here
deterministically from the pantry items' own known macro values -
never from anything the model claims. This also means we can catch and
reject a recipe that references an ingredient not in the pantry, or
asks for more of something than is actually available, rather than
silently trusting made-up numbers.

The LLM call itself is injected as a parameter (`llm_call_fn`) so this
logic can be fully unit-tested without a running Ollama instance -
generate_recipe() defaults to the real call_ollama, but tests pass in a
fake function that returns canned responses.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.core.budget_split import MacroBudget
from app.core.macro_fit import score_fit
from app.core.ollama_client import call_ollama, parse_json_response


class PantryItemInput(BaseModel):
    id: str
    name: str
    quantity: Optional[float]
    unit: Optional[str]
    protein: Optional[float]
    carb: Optional[float]
    fat: Optional[float]
    cal: Optional[float]


class RecipeIngredientUsed(BaseModel):
    pantry_item_id: str
    name: str
    quantity_used: float
    unit: str


class GeneratedRecipe(BaseModel):
    recipe_name: str
    steps: list[str]
    ingredients_used: list[RecipeIngredientUsed]
    protein: float
    carb: float
    fat: float
    cal: float
    fit_score: float


class RecipeGenerationError(Exception):
    pass


def build_recipe_prompt(pantry_items: list[PantryItemInput], target: MacroBudget) -> str:
    ingredient_lines = "\n".join(
        f"- id: {item.id}, name: {item.name}, available: {item.quantity} {item.unit}"
        for item in pantry_items
        if item.quantity is not None and item.unit is not None
    )

    return f"""You are a recipe assistant. Given the pantry ingredients below and a
macro budget, choose a subset of these ingredients (using no more than the
available quantity of each) and write a simple step-by-step recipe.

Pantry ingredients:
{ingredient_lines}

Macro budget target: {target.protein}g protein, {target.carb}g carb, {target.fat}g fat, {target.cal} calories.

Respond with ONLY a JSON object in this exact shape, nothing else:
{{
  "recipe_name": "<short name>",
  "steps": ["<step 1>", "<step 2>", ...],
  "ingredients_used": [
    {{"pantry_item_id": "<id from the list above>", "quantity_used": <number, in the same unit as listed>}}
  ]
}}

Only reference pantry_item_id values from the list above. Do not invent ingredients."""


def compute_scaled_macros(pantry_item: PantryItemInput, quantity_used: float) -> MacroBudget:
    """
    Scales a pantry item's known macros proportionally to how much of it
    was actually used, e.g. if 200g has 46g protein and the recipe uses
    100g, that's 23g protein - computed here, never trusted from the LLM
    or from the client at accept-time.
    """
    if pantry_item.quantity is None or pantry_item.quantity == 0:
        raise RecipeGenerationError(
            f"Pantry item '{pantry_item.name}' has no quantity on record - can't scale its macros."
        )
    if quantity_used > pantry_item.quantity:
        raise RecipeGenerationError(
            f"Recipe asked for {quantity_used}{pantry_item.unit} of '{pantry_item.name}', "
            f"but only {pantry_item.quantity}{pantry_item.unit} is available."
        )

    scale = quantity_used / pantry_item.quantity
    return MacroBudget(
        protein=(pantry_item.protein or 0) * scale,
        carb=(pantry_item.carb or 0) * scale,
        fat=(pantry_item.fat or 0) * scale,
        cal=(pantry_item.cal or 0) * scale,
    )


def generate_recipe(
    pantry_items: list[PantryItemInput],
    target: MacroBudget,
    llm_call_fn=call_ollama,
) -> GeneratedRecipe:
    prompt = build_recipe_prompt(pantry_items, target)
    raw_response = llm_call_fn(prompt)
    parsed = parse_json_response(raw_response)

    if "recipe_name" not in parsed or "steps" not in parsed or "ingredients_used" not in parsed:
        raise RecipeGenerationError(f"LLM response missing required fields: {parsed}")

    pantry_by_id = {item.id: item for item in pantry_items}

    total = MacroBudget(protein=0, carb=0, fat=0, cal=0)
    ingredients_used = []

    for ingredient in parsed["ingredients_used"]:
        pantry_item_id = ingredient.get("pantry_item_id")
        quantity_used = ingredient.get("quantity_used")

        if pantry_item_id not in pantry_by_id:
            raise RecipeGenerationError(
                f"LLM referenced pantry_item_id '{pantry_item_id}' which isn't in the pantry."
            )
        if not isinstance(quantity_used, (int, float)) or quantity_used <= 0:
            raise RecipeGenerationError(f"Invalid quantity_used for '{pantry_item_id}': {quantity_used}")

        pantry_item = pantry_by_id[pantry_item_id]
        scaled = compute_scaled_macros(pantry_item, quantity_used)

        total = MacroBudget(
            protein=total.protein + scaled.protein,
            carb=total.carb + scaled.carb,
            fat=total.fat + scaled.fat,
            cal=total.cal + scaled.cal,
        )

        ingredients_used.append(RecipeIngredientUsed(
            pantry_item_id=pantry_item_id,
            name=pantry_item.name,
            quantity_used=quantity_used,
            unit=pantry_item.unit or "",
        ))

    if not ingredients_used:
        raise RecipeGenerationError("LLM did not select any ingredients.")

    fit = score_fit(total, target)

    return GeneratedRecipe(
        recipe_name=parsed["recipe_name"],
        steps=parsed["steps"],
        ingredients_used=ingredients_used,
        protein=round(total.protein, 2),
        carb=round(total.carb, 2),
        fat=round(total.fat, 2),
        cal=round(total.cal, 2),
        fit_score=round(fit, 4),
    )
