from typing import Optional

from pydantic import BaseModel

from app.core.budget_split import SplitMode


class StandaloneBudgetRequest(BaseModel):
    """
    A one-off macro budget typed in directly by the user - no Daily
    Target or Food Log involved. Optionally split (full/partial/N-way)
    using the same math as Mode A.
    """
    protein: float
    carb: float
    fat: float
    cal: float
    split_mode: SplitMode = SplitMode.FULL
    split_value: Optional[float] = None  # percentage for PARTIAL, meal count for MEALS


class StandaloneBudgetOut(BaseModel):
    protein: float
    carb: float
    fat: float
    cal: float


class AddToDailyRequest(BaseModel):
    """What was actually eaten under the standalone flow, to be logged."""
    name: str
    protein: float
    carb: float
    fat: float
    cal: float


class AddToDailyOut(BaseModel):
    """
    Confirms the entry was logged, plus the resulting remaining macros -
    or, if no Daily Target exists yet, a flag saying so along with the
    raw negative totals (nothing to subtract from, so we show what's
    "in the hole" starting from zero rather than silently failing).
    """
    logged_entry_id: str
    has_daily_target: bool
    remaining_protein: Optional[float] = None
    remaining_carb: Optional[float] = None
    remaining_fat: Optional[float] = None
    remaining_cal: Optional[float] = None
    message: str
