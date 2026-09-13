from pydantic import BaseModel


class IntentParseRequest(BaseModel):
    text: str


class ClarificationAttribute(BaseModel):
    key: str
    label: str
    options: list[str]


class IntentParseOut(BaseModel):
    category: str
    is_broad: bool
    mentioned_attributes: dict[str, str]
    # Empty if the request was already specific enough, or if the
    # category has no clarifying attributes defined. Populated (tappable
    # UI options) only when clarification is actually needed.
    clarification_options: list[ClarificationAttribute]
