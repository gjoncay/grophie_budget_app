"""Seeds Plaid's 16 top-level Personal Finance Category groups.

Detailed (leaf) categories aren't hand-seeded here — they're created
on-the-fly as children of these groups when real transactions sync in
Phase 3, since Plaid's full detailed taxonomy runs to ~100+ values and
guessing at labels without real transaction data isn't worth it.
"""

from app.db import SessionLocal
from app.models import Category

PRIMARY_CATEGORIES = [
    ("INCOME", "Income"),
    ("TRANSFER_IN", "Transfers In"),
    ("TRANSFER_OUT", "Transfers Out"),
    ("LOAN_PAYMENTS", "Loan Payments"),
    ("BANK_FEES", "Bank Fees"),
    ("ENTERTAINMENT", "Entertainment"),
    ("FOOD_AND_DRINK", "Food and Drink"),
    ("GENERAL_MERCHANDISE", "Shopping"),
    ("HOME_IMPROVEMENT", "Home Improvement"),
    ("MEDICAL", "Medical"),
    ("PERSONAL_CARE", "Personal Care"),
    ("GENERAL_SERVICES", "Services"),
    ("GOVERNMENT_AND_NON_PROFIT", "Government & Non-Profit"),
    ("TRANSPORTATION", "Transportation"),
    ("TRAVEL", "Travel"),
    ("RENT_AND_UTILITIES", "Rent & Utilities"),
]


def seed_categories() -> None:
    with SessionLocal() as db:
        existing_groups = {c.group for c in db.query(Category).all()}
        for group, name in PRIMARY_CATEGORIES:
            if group in existing_groups:
                continue
            db.add(Category(name=name, group=group, is_custom=False))
        db.commit()


if __name__ == "__main__":
    seed_categories()
