from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import networth, plaid_client, security, sync
from app.db import get_db
from app.models import Account, PlaidItem

router = APIRouter(prefix="/api/plaid", tags=["plaid"])


class ExchangeRequest(BaseModel):
    public_token: str


@router.post("/link-token")
def link_token():
    try:
        return {"link_token": plaid_client.create_link_token()}
    except plaid_client.PlaidNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/exchange")
def exchange(body: ExchangeRequest, db: Session = Depends(get_db)):
    try:
        exchanged = plaid_client.exchange_public_token(body.public_token)
        accounts, institution_name = plaid_client.get_accounts(
            exchanged["access_token"]
        )
    except plaid_client.PlaidNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))

    item = PlaidItem(
        plaid_item_id=exchanged["item_id"],
        institution_name=institution_name,
        access_token=security.encrypt(exchanged["access_token"]),
    )
    db.add(item)
    db.flush()

    for account in accounts:
        db.add(Account(item_id=item.id, **account))
    db.flush()

    # Backfill whatever transaction history Plaid has for this item right
    # away, so the Transactions/Dashboard screens aren't empty after connecting.
    backfill = sync.sync_item_transactions(db, item)
    networth.recompute_net_worth_history(db)

    return {
        "item_id": item.id,
        "institution_name": item.institution_name,
        "accounts_added": len(accounts),
        "transactions_added": backfill["added"],
    }


@router.post("/items/{item_id}/sync")
def sync_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(PlaidItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        result = sync.sync_item_transactions(db, item)
    except plaid_client.PlaidNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
    networth.recompute_net_worth_history(db)
    return result


@router.get("/items")
def list_items(db: Session = Depends(get_db)):
    return [
        {
            "id": i.id,
            "institution_name": i.institution_name,
            "status": i.status,
            "last_synced_at": i.last_synced_at,
        }
        for i in db.query(PlaidItem).all()
    ]


@router.delete("/items/{item_id}")
def remove_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(PlaidItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        plaid_client.remove_item(security.decrypt(item.access_token))
    except plaid_client.PlaidNotConfigured:
        pass  # allow removing a locally-stored item even without live Plaid creds
    db.delete(item)
    db.commit()
    return {"ok": True}
