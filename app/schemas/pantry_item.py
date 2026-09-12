from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PantryItemCreate(BaseModel):
    name: str
    barcode: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    protein: Optional[float] = None
    carb: Optional[float] = None
    fat: Optional[float] = None
    cal: Optional[float] = None


class PantryItemUpdate(BaseModel):
    """All fields optional - a PATCH-style partial update."""
    name: Optional[str] = None
    barcode: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    protein: Optional[float] = None
    carb: Optional[float] = None
    fat: Optional[float] = None
    cal: Optional[float] = None


class PantryItemOut(BaseModel):
    id: UUID
    name: str
    barcode: Optional[str]
    quantity: Optional[float]
    unit: Optional[str]
    protein: Optional[float]
    carb: Optional[float]
    fat: Optional[float]
    cal: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True
