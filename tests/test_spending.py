from datetime import date

from app import spending
from app.models import Account, BudgetTarget, Category, PlaidItem, Transaction


def _make_account(db_session):
    item = PlaidItem(plaid_item_id="item-spend", institution_name="Fake Bank", access_token="x")
    db_session.add(item)
    db_session.flush()
    account = Account(
        item_id=item.id,
        plaid_account_id="acc-spend",
        name="Checking",
        type="depository",
        current_balance=1000.0,
        currency="USD",
    )
    db_session.add(account)
    db_session.flush()
    return account


def _food_category(db_session):
    return db_session.query(Category).filter_by(group="FOOD_AND_DRINK").one()


def test_summary_excludes_income_and_rolls_up_leaf_categories(db_session):
    account = _make_account(db_session)
    food = _food_category(db_session)
    coffee = Category(name="Coffee", group="FOOD_AND_DRINK_COFFEE", parent_category_id=food.id)
    db_session.add(coffee)
    db_session.flush()

    month = spending.current_month()
    year, mon = map(int, month.split("-"))
    this_month_date = date(year, mon, 15)

    db_session.add_all(
        [
            Transaction(
                account_id=account.id, plaid_transaction_id="t1", date=this_month_date,
                amount=20.0, category_id=food.id,
            ),
            Transaction(
                account_id=account.id, plaid_transaction_id="t2", date=this_month_date,
                amount=30.0, category_id=coffee.id,
            ),
            Transaction(
                account_id=account.id, plaid_transaction_id="t3", date=this_month_date,
                amount=-1000.0, category_id=None,  # a deposit; not spending
            ),
        ]
    )
    db_session.commit()

    summary = spending.get_spending_summary(db_session, month)
    assert summary["total_spending"] == 50.0
    assert summary["by_category"] == [{"category_id": food.id, "category_name": "Food and Drink", "amount": 50.0}]


def test_trend_covers_requested_number_of_months(db_session):
    account = _make_account(db_session)
    food = _food_category(db_session)
    month = spending.current_month()

    for offset in range(3):
        m = spending._shift_month(month, offset)
        y, mo = map(int, m.split("-"))
        db_session.add(
            Transaction(
                account_id=account.id,
                plaid_transaction_id=f"t-{offset}",
                date=date(y, mo, 10),
                amount=10.0 * (offset + 1),
                category_id=food.id,
            )
        )
    db_session.commit()

    trend = spending.get_spending_trend(db_session, 3)
    assert [t["month"] for t in trend] == [
        spending._shift_month(month, 2),
        spending._shift_month(month, 1),
        month,
    ]
    assert trend[-1]["total"] == 10.0  # offset=0 -> current month


def test_budget_progress_recurring_vs_specific_month(db_session, client):
    account = _make_account(db_session)
    food = _food_category(db_session)
    month = spending.current_month()
    year, mon = map(int, month.split("-"))

    db_session.add(
        Transaction(
            account_id=account.id, plaid_transaction_id="t1", date=date(year, mon, 5),
            amount=50.0, category_id=food.id,
        )
    )
    db_session.add(BudgetTarget(category_id=food.id, target_amount=100.0, month=None))
    last_month = spending._shift_month(month, 1)
    db_session.add(BudgetTarget(category_id=food.id, target_amount=999.0, month=last_month))
    db_session.commit()

    progress = spending.get_budget_progress(db_session, month)
    assert len(progress) == 1  # the specific-month target for last month shouldn't apply
    assert progress[0]["target_amount"] == 100.0
    assert progress[0]["actual_amount"] == 50.0
    assert progress[0]["pct_used"] == 0.5


def test_budget_targets_crud_via_api(client, db_session):
    food = _food_category(db_session)

    create_response = client.post(
        "/api/budget-targets", json={"category_id": food.id, "target_amount": 300.0}
    )
    assert create_response.status_code == 200
    target_id = create_response.json()["id"]

    update_response = client.put(f"/api/budget-targets/{target_id}", json={"target_amount": 400.0})
    assert update_response.status_code == 200
    assert update_response.json()["target_amount"] == 400.0

    list_response = client.get("/api/budget-targets")
    assert len(list_response.json()) == 1
