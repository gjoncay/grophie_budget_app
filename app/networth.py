"""Builds the net worth trend. Depository/credit/loan balances are
reconstructed backward through transaction history: each transaction's
Plaid amount (positive = money out) was already subtracted from the
balance on its date, so undoing day d's transactions — balance_end(d-1)
= balance_end(d) + sum(amounts on day d) — walks the balance backward
one day at a time from today's current_balance. Investment accounts have
no historical-holdings API, so their current balance only counts from
the day the account was connected forward — see the plan's caveat.
"""
import json
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Account, NetWorthSnapshot

RECONSTRUCTABLE_TYPES = ("depository", "credit", "loan")
ASSET_TYPES = ("depository", "investment")


def _reconstruct_balances(account: Account, start: date, end: date) -> dict[date, float]:
    if account.current_balance is None:
        return {}
    amount_by_date: dict[date, float] = defaultdict(float)
    for t in account.transactions:
        amount_by_date[t.date] += t.amount

    balances: dict[date, float] = {}
    balance = account.current_balance
    d = end
    while d >= start:
        balances[d] = balance
        balance += amount_by_date.get(d, 0.0)
        d -= timedelta(days=1)
    return balances


def recompute_net_worth_history(db: Session) -> int:
    accounts = db.query(Account).filter_by(is_hidden=False).all()
    transaction_dates = [t.date for a in accounts for t in a.transactions]
    if not transaction_dates:
        return 0

    start = min(transaction_dates)
    end = date.today()

    reconstructable = [a for a in accounts if a.type in RECONSTRUCTABLE_TYPES]
    balances_by_account = {a.id: _reconstruct_balances(a, start, end) for a in reconstructable}
    investment_accounts = [a for a in accounts if a.type == "investment"]

    written = 0
    d = start
    while d <= end:
        assets = 0.0
        liabilities = 0.0
        breakdown = {"depository": 0.0, "credit": 0.0, "loan": 0.0, "investment": 0.0}

        for a in reconstructable:
            balance = balances_by_account[a.id].get(d)
            if balance is None:
                continue
            if a.type in ASSET_TYPES:
                assets += balance
            else:
                liabilities += balance
            breakdown[a.type] += balance

        for a in investment_accounts:
            connected_date = a.item.created_at.date()
            if d >= connected_date and a.current_balance is not None:
                assets += a.current_balance
                breakdown["investment"] += a.current_balance

        snapshot = db.query(NetWorthSnapshot).filter_by(snapshot_date=d).one_or_none()
        if snapshot is None:
            snapshot = NetWorthSnapshot(snapshot_date=d)
            db.add(snapshot)
        snapshot.total_assets = assets
        snapshot.total_liabilities = liabilities
        snapshot.net_worth = assets - liabilities
        snapshot.breakdown_json = json.dumps(breakdown)
        written += 1
        d += timedelta(days=1)

    db.commit()
    return written


def build_insight(db: Session) -> str:
    latest = db.query(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date.desc()).first()
    if latest is None:
        return "Connect an account to start tracking your net worth."

    month_ago = latest.snapshot_date - timedelta(days=30)
    prior = (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.snapshot_date <= month_ago)
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .first()
    )
    if prior is None:
        return f"Your net worth is {_fmt(latest.net_worth)}."

    change = latest.net_worth - prior.net_worth
    if change > 0:
        return f"You're up {_fmt(change)} over the last month — nice work."
    if change < 0:
        return f"You're down {_fmt(abs(change))} over the last month."
    return "Your net worth held steady over the last month."


def _fmt(amount: float) -> str:
    return f"${amount:,.0f}"
