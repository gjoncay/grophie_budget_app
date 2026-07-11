from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import spending
from app.db import get_db
from app.models import BudgetTarget, Category

router = APIRouter(prefix="/api/budget-targets", tags=["budget-targets"])


class CreateTargetRequest(BaseModel):
    category_id: int
    target_amount: float
    month: str | None = None  # None = recurring every month


class UpdateTargetRequest(BaseModel):
    target_amount: float | None = None
    active: bool | None = None


def _serialize(t: BudgetTarget) -> dict:
    return {
        "id": t.id,
        "category_id": t.category_id,
        "category_name": t.category.name,
        "month": t.month,
        "target_amount": t.target_amount,
        "active": t.active,
    }


@router.get("")
def list_targets(db: Session = Depends(get_db)):
    return [_serialize(t) for t in db.query(BudgetTarget).order_by(BudgetTarget.id).all()]


@router.post("")
def create_target(body: CreateTargetRequest, db: Session = Depends(get_db)):
    if not db.get(Category, body.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    target = BudgetTarget(
        category_id=body.category_id, target_amount=body.target_amount, month=body.month
    )
    db.add(target)
    db.commit()
    return _serialize(target)


@router.put("/{target_id}")
def update_target(target_id: int, body: UpdateTargetRequest, db: Session = Depends(get_db)):
    target = db.get(BudgetTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if body.target_amount is not None:
        target.target_amount = body.target_amount
    if body.active is not None:
        target.active = body.active
    db.commit()
    return _serialize(target)


@router.get("/progress")
def progress(month: str | None = None, db: Session = Depends(get_db)):
    return spending.get_budget_progress(db, month or spending.current_month())
