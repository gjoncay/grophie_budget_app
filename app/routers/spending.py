from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import spending
from app.db import get_db

router = APIRouter(prefix="/api/spending", tags=["spending"])


@router.get("/summary")
def summary(month: str | None = None, db: Session = Depends(get_db)):
    return spending.get_spending_summary(db, month or spending.current_month())


@router.get("/trend")
def trend(months: int = 6, db: Session = Depends(get_db)):
    return spending.get_spending_trend(db, months)
