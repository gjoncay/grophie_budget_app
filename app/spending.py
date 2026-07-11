"""Spending is visibility-first: everything here answers "where did the
money go," not "did we stay under budget." Budget targets are the one
optional actual-vs-target feature layered on top.
"""
from collections import defaultdict
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BudgetTarget, Category, Transaction


def _month_bounds(month: str) -> tuple[date, date]:
    year, mon = (int(p) for p in month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end


def _shift_month(month: str, offset: int) -> str:
    year, mon = (int(p) for p in month.split("-"))
    total = mon - offset
    while total <= 0:
        total += 12
        year -= 1
    while total > 12:
        total -= 12
        year += 1
    return f"{year:04d}-{total:02d}"


def _root_category(db: Session, category: Category) -> Category:
    while category.parent_category_id is not None:
        category = db.get(Category, category.parent_category_id)
    return category


def current_month() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def get_spending_summary(db: Session, month: str) -> dict:
    start, end = _month_bounds(month)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.date >= start, Transaction.date < end, Transaction.amount > 0)
        .all()
    )

    totals: dict[int | None, float] = defaultdict(float)
    names: dict[int | None, str] = {}
    for t in transactions:
        if t.category_id is None:
            key, name = None, "Uncategorized"
        else:
            root = _root_category(db, t.category)
            key, name = root.id, root.name
        totals[key] += t.amount
        names[key] = name

    by_category = sorted(
        (
            {"category_id": key, "category_name": names[key], "amount": amount}
            for key, amount in totals.items()
        ),
        key=lambda row: -row["amount"],
    )
    return {"month": month, "total_spending": sum(totals.values()), "by_category": by_category}


def get_spending_trend(db: Session, months: int) -> list[dict]:
    latest = current_month()
    return [
        {"month": m, "total": get_spending_summary(db, m)["total_spending"]}
        for m in (_shift_month(latest, offset) for offset in range(months - 1, -1, -1))
    ]


def _category_and_descendant_ids(db: Session, category_id: int) -> list[int]:
    ids = [category_id]
    ids.extend(c.id for c in db.query(Category).filter_by(parent_category_id=category_id).all())
    return ids


def get_budget_progress(db: Session, month: str) -> list[dict]:
    targets = (
        db.query(BudgetTarget)
        .filter_by(active=True)
        .filter((BudgetTarget.month.is_(None)) | (BudgetTarget.month == month))
        .all()
    )
    start, end = _month_bounds(month)

    progress = []
    for target in targets:
        category_ids = _category_and_descendant_ids(db, target.category_id)
        actual = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.category_id.in_(category_ids),
                Transaction.date >= start,
                Transaction.date < end,
                Transaction.amount > 0,
            )
            .scalar()
            or 0.0
        )
        progress.append(
            {
                "id": target.id,
                "category_id": target.category_id,
                "category_name": target.category.name,
                "target_amount": target.target_amount,
                "actual_amount": actual,
                "pct_used": actual / target.target_amount if target.target_amount else None,
            }
        )
    return progress
