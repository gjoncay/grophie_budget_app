from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Account, NetWorthSnapshot
from app.networth import ASSET_TYPES

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _serialize(a: Account) -> dict:
    return {
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


@router.get("")
def list_accounts(db: Session = Depends(get_db)):
    return [_serialize(a) for a in db.query(Account).filter_by(is_hidden=False).all()]


@router.get("/summary")
def accounts_summary(db: Session = Depends(get_db)):
    accounts = db.query(Account).filter_by(is_hidden=False).all()
    latest = db.query(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date.desc()).first()
    if latest:
        net_worth, total_assets, total_liabilities, as_of = (
            latest.net_worth,
            latest.total_assets,
            latest.total_liabilities,
            latest.snapshot_date,
        )
    else:
        total_assets = sum(a.current_balance or 0 for a in accounts if a.type in ASSET_TYPES)
        total_liabilities = sum(a.current_balance or 0 for a in accounts if a.type not in ASSET_TYPES)
        net_worth = total_assets - total_liabilities
        as_of = None
    return {
        "net_worth": net_worth,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "as_of": as_of,
        "accounts": [_serialize(a) for a in accounts],
    }
