"""Syncs holdings/securities/investment activity for an item's investment
accounts, and serves the read-side aggregation (latest holdings with
gain/loss, allocation by asset class) the Investments screen needs.
"""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import plaid_client, security
from app.models import Holding, InvestmentTransaction, PlaidItem, Security

BACKFILL_WINDOW_DAYS = 730


def _upsert_securities(db: Session, securities: list[dict]) -> None:
    for s in securities:
        existing = db.query(Security).filter_by(plaid_security_id=s["plaid_security_id"]).one_or_none()
        if existing is None:
            db.add(Security(**s))
        else:
            for key, value in s.items():
                setattr(existing, key, value)
    db.flush()


def sync_item_investments(db: Session, item: PlaidItem) -> dict:
    investment_accounts = [a for a in item.accounts if a.type == "investment"]
    if not investment_accounts:
        return {"holdings": 0, "investment_transactions": 0}

    access_token = security.decrypt(item.access_token)
    accounts_by_plaid_id = {a.plaid_account_id: a for a in investment_accounts}
    today = date.today()

    holdings_result = plaid_client.get_investment_holdings(access_token)
    _upsert_securities(db, holdings_result["securities"])

    holdings_written = 0
    for h in holdings_result["holdings"]:
        account = accounts_by_plaid_id.get(h["account_id"])
        if account is None:
            continue
        security_row = db.query(Security).filter_by(plaid_security_id=h["security_id"]).one_or_none()
        if security_row is None:
            continue
        holding = (
            db.query(Holding)
            .filter_by(account_id=account.id, security_id=security_row.id, snapshot_date=today)
            .one_or_none()
        )
        if holding is None:
            holding = Holding(account_id=account.id, security_id=security_row.id, snapshot_date=today)
            db.add(holding)
        holding.quantity = h["quantity"]
        holding.cost_basis = h["cost_basis"]
        holding.institution_price = h["institution_price"]
        holding.institution_value = h["institution_value"]
        holdings_written += 1

    tx_result = plaid_client.get_investment_transactions(
        access_token, today - timedelta(days=BACKFILL_WINDOW_DAYS), today
    )
    _upsert_securities(db, tx_result["securities"])

    tx_written = 0
    for t in tx_result["investment_transactions"]:
        account = accounts_by_plaid_id.get(t["account_id"])
        if account is None:
            continue
        if (
            db.query(InvestmentTransaction)
            .filter_by(plaid_investment_transaction_id=t["plaid_investment_transaction_id"])
            .first()
        ):
            continue
        security_row = (
            db.query(Security).filter_by(plaid_security_id=t["security_id"]).one_or_none()
            if t.get("security_id")
            else None
        )
        db.add(
            InvestmentTransaction(
                plaid_investment_transaction_id=t["plaid_investment_transaction_id"],
                account_id=account.id,
                security_id=security_row.id if security_row else None,
                date=t["date"],
                type=t["type"],
                quantity=t["quantity"],
                price=t["price"],
                amount=t["amount"],
                name=t["name"],
            )
        )
        tx_written += 1

    db.commit()
    return {"holdings": holdings_written, "investment_transactions": tx_written}


def get_latest_holdings(db: Session) -> list[dict]:
    latest_date = db.query(func.max(Holding.snapshot_date)).scalar()
    if latest_date is None:
        return []

    result = []
    for h in db.query(Holding).filter_by(snapshot_date=latest_date).all():
        value = h.institution_value
        if value is None and h.institution_price is not None:
            value = h.quantity * h.institution_price
        gain_loss = value - h.cost_basis if value is not None and h.cost_basis else None
        gain_loss_pct = gain_loss / h.cost_basis if gain_loss is not None and h.cost_basis else None
        result.append(
            {
                "account_id": h.account_id,
                "account_name": h.account.name,
                "security_id": h.security_id,
                "ticker_symbol": h.security.ticker_symbol,
                "name": h.security.name,
                "security_type": h.security.security_type,
                "quantity": h.quantity,
                "cost_basis": h.cost_basis,
                "value": value,
                "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct,
                "as_of": h.snapshot_date,
            }
        )
    return result


def get_allocation(db: Session) -> dict:
    holdings = get_latest_holdings(db)
    allocation: dict[str, float] = defaultdict(float)
    total_value = 0.0
    total_cost_basis = 0.0
    for h in holdings:
        if h["value"] is not None:
            allocation[h["security_type"] or "other"] += h["value"]
            total_value += h["value"]
        if h["cost_basis"]:
            total_cost_basis += h["cost_basis"]
    total_gain_loss = total_value - total_cost_basis if total_cost_basis else None
    return {
        "allocation": dict(allocation),
        "total_value": total_value,
        "total_cost_basis": total_cost_basis,
        "total_gain_loss": total_gain_loss,
    }
