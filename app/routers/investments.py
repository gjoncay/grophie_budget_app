from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import investments
from app.db import get_db
from app.models import InvestmentTransaction

router = APIRouter(prefix="/api/investments", tags=["investments"])


@router.get("/holdings")
def holdings(db: Session = Depends(get_db)):
    return investments.get_latest_holdings(db)


@router.get("/performance")
def performance(db: Session = Depends(get_db)):
    return investments.get_allocation(db)


@router.get("/transactions")
def transactions(db: Session = Depends(get_db)):
    query = (
        db.query(InvestmentTransaction)
        .order_by(InvestmentTransaction.date.desc(), InvestmentTransaction.id.desc())
        .limit(200)
    )
    return [
        {
            "id": t.id,
            "account_id": t.account_id,
            "account_name": t.account.name,
            "security_name": t.security.name if t.security else None,
            "ticker_symbol": t.security.ticker_symbol if t.security else None,
            "date": t.date,
            "type": t.type,
            "quantity": t.quantity,
            "price": t.price,
            "amount": t.amount,
            "name": t.name,
        }
        for t in query.all()
    ]
