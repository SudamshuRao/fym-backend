"""
Daily Target endpoints. There's no separate create/update distinction in
the API - PUT always upserts, since "set once, persists until updated"
means the client never needs to know whether a target already exists.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.daily_target import DailyTarget
from app.models.user import User
from app.schemas.daily_target import DailyTargetSet, DailyTargetOut

router = APIRouter(prefix="/daily-target", tags=["daily-target"])


@router.put("", response_model=DailyTargetOut)
def set_daily_target(
    payload: DailyTargetSet,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = db.query(DailyTarget).filter(DailyTarget.user_id == current_user.id).first()

    if target is None:
        target = DailyTarget(user_id=current_user.id, **payload.dict())
        db.add(target)
    else:
        target.protein = payload.protein
        target.carb = payload.carb
        target.fat = payload.fat
        target.cal = payload.cal

    db.commit()
    db.refresh(target)
    return target


@router.get("", response_model=DailyTargetOut)
def get_daily_target(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = db.query(DailyTarget).filter(DailyTarget.user_id == current_user.id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="No daily target set yet")
    return target
