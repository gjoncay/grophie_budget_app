from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Account

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).filter_by(is_hidden=False).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "official_name": a.official_name,
            "type": a.type,
            "subtype": a.subtype,
            "mask": a.mask,
            "current_balance": a.current_balance,
            "available_balance": a.available_balance,
            "currency": a.currency,
            "institution_name": a.item.institution_name,
        }
        for a in accounts
    ]
