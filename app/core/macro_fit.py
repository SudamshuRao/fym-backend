"""
Macro-fit scoring: given a target macro budget and a candidate food item
(a recipe, a restaurant menu item, anything with protein/carb/fat/cal),
returns a fit score - how well the candidate matches the budget.

Deliberately pure/stateless, no DB, no LLM - this is arithmetic, and
arithmetic doesn't need a model. Shared by both the cook path (Phase 3
pantry recipes) and the eat-out path (Phase 3 restaurant matching).

Scoring approach: normalized weighted deviation. Each macro's deviation
from the budget is expressed as a fraction of the budget itself (so a
10g protein miss matters differently on a 20g budget than a 200g one),
then combined into a single score where 0 = perfect fit and higher =
worse fit. Calories get a lower weight than the individual macros by
default, since hitting protein/carb/fat precisely usually matters more
to the user than calories alone (calories are a downstream consequence
of the other three).
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.budget_split import MacroBudget


class ScoreWeights(BaseModel):
    protein: float = 1.0
    carb: float = 1.0
    fat: float = 1.0
    cal: float = 0.5


DEFAULT_WEIGHTS = ScoreWeights()


def _safe_relative_deviation(actual: float, target: float) -> float:
    """
    |actual - target| / target, but guards against target == 0 (e.g. a
    zero-carb budget) by falling back to the raw absolute difference so
    we don't divide by zero or produce an undefined score.
    """
    if target == 0:
        return abs(actual)
    return abs(actual - target) / abs(target)


def score_fit(
    candidate: MacroBudget,
    target: MacroBudget,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> float:
    """
    Lower is better. 0.0 means the candidate exactly matches the target
    budget on every macro. There's no fixed upper bound - a candidate
    wildly over or under the budget just produces a larger number.
    """
    protein_dev = _safe_relative_deviation(candidate.protein, target.protein)
    carb_dev = _safe_relative_deviation(candidate.carb, target.carb)
    fat_dev = _safe_relative_deviation(candidate.fat, target.fat)
    cal_dev = _safe_relative_deviation(candidate.cal, target.cal)

    weighted_sum = (
        protein_dev * weights.protein
        + carb_dev * weights.carb
        + fat_dev * weights.fat
        + cal_dev * weights.cal
    )
    total_weight = weights.protein + weights.carb + weights.fat + weights.cal
    return weighted_sum / total_weight


def rank_candidates(
    candidates: list[tuple[str, MacroBudget]],
    target: MacroBudget,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
    limit: int | None = None,
) -> list[tuple[str, MacroBudget, float]]:
    """
    Takes a list of (identifier, macros) pairs, scores each against the
    target, and returns them sorted best-fit-first as
    (identifier, macros, score) triples. `identifier` is caller-defined -
    e.g. a menu item name or a recipe id.
    """
    scored = [(identifier, macros, score_fit(macros, target, weights)) for identifier, macros in candidates]
    scored.sort(key=lambda triple: triple[2])
    return scored[:limit] if limit is not None else scored
