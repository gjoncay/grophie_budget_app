"""Turns raw Plaid transaction data into Transaction rows: resolves each
transaction's category (via user-taught CategoryRules first, then Plaid's
own primary/detailed taxonomy) and keeps PlaidItem sync cursors current.
"""
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import plaid_client, security
from app.models import Account, Category, CategoryRule, PlaidItem, Transaction


def _humanize(detailed: str, primary: str) -> str:
    suffix = detailed[len(primary) :].lstrip("_") if detailed.startswith(primary) else detailed
    words = suffix.replace("_", " ").strip().split()
    return " ".join(w.capitalize() for w in words) if words else detailed.replace("_", " ").title()


def _resolve_plaid_taxonomy_category(db: Session, primary: str | None, detailed: str | None) -> int | None:
    if not primary:
        return None
    parent = db.query(Category).filter_by(group=primary, parent_category_id=None).one_or_none()
    if parent is None:
        return None
    if not detailed or detailed == primary:
        return parent.id
    leaf = db.query(Category).filter_by(group=detailed, parent_category_id=parent.id).one_or_none()
    if leaf is None:
        leaf = Category(
            name=_humanize(detailed, primary),
            group=detailed,
            parent_category_id=parent.id,
            is_custom=False,
        )
        db.add(leaf)
        db.flush()
    return leaf.id


def resolve_category(db: Session, tx: dict) -> int | None:
    merchant = (tx.get("merchant_name") or tx.get("description") or "").strip().lower()
    rules = db.query(CategoryRule).order_by(CategoryRule.priority.desc(), CategoryRule.id.asc()).all()
    for rule in rules:
        if rule.match_type == "merchant_exact" and merchant and merchant == rule.match_value.lower():
            return rule.category_id
        if rule.match_type == "merchant_contains" and merchant and rule.match_value.lower() in merchant:
            return rule.category_id
        if rule.match_type == "plaid_category_equals" and tx.get("plaid_raw_category") == rule.match_value:
            return rule.category_id
    return _resolve_plaid_taxonomy_category(
        db, tx.get("plaid_raw_category"), tx.get("plaid_raw_category_detailed")
    )


def sync_item_transactions(db: Session, item: PlaidItem) -> dict:
    access_token = security.decrypt(item.access_token)
    result = plaid_client.sync_transactions(access_token, item.sync_cursor)

    accounts_by_plaid_id = {a.plaid_account_id: a for a in item.accounts}

    added = 0
    for tx in result["added"]:
        account = accounts_by_plaid_id.get(tx["account_id"])
        if account is None:
            continue
        if db.query(Transaction).filter_by(plaid_transaction_id=tx["plaid_transaction_id"]).first():
            continue
        db.add(
            Transaction(
                account_id=account.id,
                plaid_transaction_id=tx["plaid_transaction_id"],
                date=tx["date"],
                amount=tx["amount"],
                merchant_name=tx["merchant_name"],
                description=tx["description"],
                plaid_raw_category=tx["plaid_raw_category"],
                category_id=resolve_category(db, tx),
                pending=tx["pending"],
            )
        )
        added += 1

    modified = 0
    for tx in result["modified"]:
        existing = (
            db.query(Transaction).filter_by(plaid_transaction_id=tx["plaid_transaction_id"]).one_or_none()
        )
        if existing is None or existing.is_manually_recategorized:
            continue
        existing.amount = tx["amount"]
        existing.pending = tx["pending"]
        existing.merchant_name = tx["merchant_name"]
        existing.description = tx["description"]
        modified += 1

    removed = 0
    for plaid_transaction_id in result["removed"]:
        deleted = (
            db.query(Transaction).filter_by(plaid_transaction_id=plaid_transaction_id).delete()
        )
        removed += deleted

    item.sync_cursor = result["cursor"]
    item.last_synced_at = datetime.now(UTC)
    db.commit()
    return {"added": added, "modified": modified, "removed": removed}
