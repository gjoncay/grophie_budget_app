from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import networth
from app.db import get_db
from app.models import NetWorthSnapshot

router = APIRouter(tags=["dashboard"])


@router.get("/api/networth/history")
def networth_history(db: Session = Depends(get_db)):
    snapshots = db.query(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date).all()
    return [
        {
            "date": s.snapshot_date,
            "net_worth": s.net_worth,
            "total_assets": s.total_assets,
            "total_liabilities": s.total_liabilities,
        }
        for s in snapshots
    ]


@router.get("/api/insights")
def insights(db: Session = Depends(get_db)):
    return {"message": networth.build_insight(db)}
