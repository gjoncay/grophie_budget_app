from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category, CategoryRule, Transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


class RecategorizeRequest(BaseModel):
    category_id: int
    apply_to_future: bool = False


def _serialize(t: Transaction) -> dict:
    return {
        "id": t.id,
        "account_id": t.account_id,
        "account_name": t.account.name,
        "date": t.date,
        "amount": t.amount,
        "merchant_name": t.merchant_name,
        "description": t.description,
        "category_id": t.category_id,
        "category_name": t.category.name if t.category else None,
        "pending": t.pending,
        "is_manually_recategorized": t.is_manually_recategorized,
    }


@router.get("")
def list_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Transaction.merchant_name.ilike(pattern) | Transaction.description.ilike(pattern)
        )
    query = query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(offset).limit(limit)
    return [_serialize(t) for t in query.all()]


@router.patch("/{transaction_id}")
def recategorize(transaction_id: int, body: RecategorizeRequest, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if not db.get(Category, body.category_id):
        raise HTTPException(status_code=404, detail="Category not found")

    transaction.category_id = body.category_id
    transaction.is_manually_recategorized = True

    rule_created = False
    if body.apply_to_future and transaction.merchant_name:
        existing_rule = (
            db.query(CategoryRule)
            .filter_by(match_type="merchant_exact", match_value=transaction.merchant_name)
            .one_or_none()
        )
        if existing_rule:
            existing_rule.category_id = body.category_id
        else:
            db.add(
                CategoryRule(
                    match_type="merchant_exact",
                    match_value=transaction.merchant_name,
                    category_id=body.category_id,
                    created_from_transaction_id=transaction.id,
                    priority=1,
                )
            )
        rule_created = True

    db.commit()
    return {**_serialize(transaction), "rule_created": rule_created}
