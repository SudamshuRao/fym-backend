from pydantic import BaseModel


class SkipEatOutRequest(BaseModel):
    menu_item: str  # what was shown but not accepted


class SkipCookRequest(BaseModel):
    recipe_name: str


class PreferenceSummaryOut(BaseModel):
    prefers: list[str]
    avoids: list[str]


class PersonalizationRefreshOut(BaseModel):
    summary: PreferenceSummaryOut
    events_processed: int
