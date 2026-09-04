"""
Budget-splitting math: given a total macro budget, return either the full
amount, a percentage portion of it, or an even split across N meals.

Deliberately pure/stateless - no DB, no user context - so both Mode A
(splitting the derived Remaining) and Mode B (splitting a manually typed
budget) can call the exact same function rather than duplicating this
logic. Per the original architecture decision: this is arithmetic, not
something an LLM should be involved in.
"""

from __future__ import annotations  # lets "float | None" work on Python 3.9

from enum import Enum

from pydantic import BaseModel


class SplitMode(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    MEALS = "meals"


class MacroBudget(BaseModel):
    protein: float
    carb: float
    fat: float
    cal: float


def split_budget(total: MacroBudget, mode: SplitMode, value: float | None = None) -> MacroBudget:
    """
    mode=FULL:    returns `total` unchanged. `value` ignored.
    mode=PARTIAL: `value` is a percentage (0-100). Returns that percentage
                  of each macro.
    mode=MEALS:   `value` is a meal count (must be >= 1, need not be a
                  whole number of meals conceptually but must be > 0).
                  Returns an even 1/N split of each macro.
    """
    if mode == SplitMode.FULL:
        return MacroBudget(**total.dict())

    if mode == SplitMode.PARTIAL:
        if value is None or not (0 < value <= 100):
            raise ValueError("partial split requires a percentage value in (0, 100]")
        factor = value / 100
        return MacroBudget(
            protein=total.protein * factor,
            carb=total.carb * factor,
            fat=total.fat * factor,
            cal=total.cal * factor,
        )

    if mode == SplitMode.MEALS:
        if value is None or value <= 0:
            raise ValueError("meals split requires a meal count > 0")
        return MacroBudget(
            protein=total.protein / value,
            carb=total.carb / value,
            fat=total.fat / value,
            cal=total.cal / value,
        )

    raise ValueError(f"Unknown split mode: {mode}")
