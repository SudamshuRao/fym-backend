"""
Pantry Item CRUD - the user's available ingredients for the cook-path
recommendation engine. Same pattern as Food Log CRUD from Phase 1: full
create/list/update/delete, all scoped to the current user.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.pantry_item import PantryItem
from app.models.user import User
from app.schemas.pantry_item import PantryItemCreate, PantryItemUpdate, PantryItemOut

router = APIRouter(prefix="/pantry", tags=["pantry"])


@router.post("", response_model=PantryItemOut, status_code=201)
def create_pantry_item(
    payload: PantryItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = PantryItem(user_id=current_user.id, **payload.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[PantryItemOut])
def list_pantry_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(PantryItem)
        .filter(PantryItem.user_id == current_user.id)
        .order_by(PantryItem.created_at.desc())
        .all()
    )


def _get_owned_item(item_id: UUID, current_user: User, db: Session) -> PantryItem:
    item = (
        db.query(PantryItem)
        .filter(PantryItem.id == item_id, PantryItem.user_id == current_user.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Pantry item not found")
    return item


@router.patch("/{item_id}", response_model=PantryItemOut)
def update_pantry_item(
    item_id: UUID,
    payload: PantryItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(item_id, current_user, db)

    # Only overwrite fields the client actually sent (partial update).
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_pantry_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(item_id, current_user, db)
    db.delete(item)
    db.commit()
    return None
