from datetime import date

from app import plaid_client
from app.models import Category, CategoryRule, Transaction

ACCOUNTS = [
    {
        "plaid_account_id": "acc_checking_1",
        "name": "Plaid Checking",
        "official_name": "Plaid Gold Standard 0% Interest Checking",
        "type": "depository",
        "subtype": "checking",
        "mask": "0000",
        "current_balance": 500.0,
        "available_balance": 500.0,
        "currency": "USD",
    }
]


def _connect_account(client, monkeypatch, first_sync_page):
    monkeypatch.setattr(
        plaid_client,
        "exchange_public_token",
        lambda public_token: {"access_token": "access-sandbox-1", "item_id": "item-1"},
    )
    monkeypatch.setattr(plaid_client, "get_accounts", lambda access_token: (ACCOUNTS, "Fake Bank"))
    monkeypatch.setattr(
        plaid_client,
        "sync_transactions",
        lambda access_token, cursor: first_sync_page,
    )
    return client.post("/api/plaid/exchange", json={"public_token": "public-sandbox-1"})


def test_backfill_creates_transactions_with_resolved_categories(client, db_session, monkeypatch):
    first_sync_page = {
        "added": [
            {
                "plaid_transaction_id": "tx_1",
                "account_id": "acc_checking_1",
                "date": date(2026, 6, 1),
                "amount": 42.50,
                "merchant_name": "Blue Bottle Coffee",
                "description": "BLUE BOTTLE COFFEE",
                "plaid_raw_category": "FOOD_AND_DRINK",
                "plaid_raw_category_detailed": "FOOD_AND_DRINK_COFFEE",
                "pending": False,
            },
            {
                "plaid_transaction_id": "tx_2",
                "account_id": "acc_checking_1",
                "date": date(2026, 6, 2),
                "amount": 1200.0,
                "merchant_name": None,
                "description": "EMPLOYER DIRECT DEPOSIT",
                "plaid_raw_category": "INCOME",
                "plaid_raw_category_detailed": "INCOME_WAGES",
                "pending": False,
            },
        ],
        "modified": [],
        "removed": [],
        "cursor": "cursor-1",
    }
    response = _connect_account(client, monkeypatch, first_sync_page)
    assert response.status_code == 200
    assert response.json()["transactions_added"] == 2

    transactions = db_session.query(Transaction).order_by(Transaction.id).all()
    assert len(transactions) == 2

    coffee_category = db_session.get(Category, transactions[0].category_id)
    assert coffee_category.name == "Coffee"
    food_parent = db_session.get(Category, coffee_category.parent_category_id)
    assert food_parent.group == "FOOD_AND_DRINK"

    income_category = db_session.get(Category, transactions[1].category_id)
    assert income_category.name == "Wages"


def test_recategorize_with_apply_to_future_creates_rule_and_applies_on_next_sync(
    client, db_session, monkeypatch
):
    first_sync_page = {
        "added": [
            {
                "plaid_transaction_id": "tx_1",
                "account_id": "acc_checking_1",
                "date": date(2026, 6, 1),
                "amount": 15.0,
                "merchant_name": "Joe's Pizza",
                "description": "JOES PIZZA",
                "plaid_raw_category": "FOOD_AND_DRINK",
                "plaid_raw_category_detailed": "FOOD_AND_DRINK_RESTAURANT",
                "pending": False,
            }
        ],
        "modified": [],
        "removed": [],
        "cursor": "cursor-1",
    }
    _connect_account(client, monkeypatch, first_sync_page)

    transaction = db_session.query(Transaction).one()
    custom_category = Category(name="Date Night", group=None, is_custom=True)
    db_session.add(custom_category)
    db_session.commit()

    response = client.patch(
        f"/api/transactions/{transaction.id}",
        json={"category_id": custom_category.id, "apply_to_future": True},
    )
    assert response.status_code == 200
    assert response.json()["rule_created"] is True

    rule = db_session.query(CategoryRule).one()
    assert rule.match_type == "merchant_exact"
    assert rule.match_value == "Joe's Pizza"
    assert rule.category_id == custom_category.id

    # a fresh sync with a similar merchant should now land in the custom category automatically
    item_id = db_session.query(Transaction).one().account.item.id
    monkeypatch.setattr(
        plaid_client,
        "sync_transactions",
        lambda access_token, cursor: {
            "added": [
                {
                    "plaid_transaction_id": "tx_2",
                    "account_id": "acc_checking_1",
                    "date": date(2026, 6, 8),
                    "amount": 18.0,
                    "merchant_name": "Joe's Pizza",
                    "description": "JOES PIZZA",
                    "plaid_raw_category": "FOOD_AND_DRINK",
                    "plaid_raw_category_detailed": "FOOD_AND_DRINK_RESTAURANT",
                    "pending": False,
                }
            ],
            "modified": [],
            "removed": [],
            "cursor": "cursor-2",
        },
    )
    sync_response = client.post(f"/api/plaid/items/{item_id}/sync")
    assert sync_response.status_code == 200
    assert sync_response.json()["added"] == 1

    new_transaction = db_session.query(Transaction).filter_by(plaid_transaction_id="tx_2").one()
    assert new_transaction.category_id == custom_category.id


def test_transactions_endpoint_filters_and_search(client, db_session, monkeypatch):
    first_sync_page = {
        "added": [
            {
                "plaid_transaction_id": "tx_1",
                "account_id": "acc_checking_1",
                "date": date(2026, 6, 1),
                "amount": 42.50,
                "merchant_name": "Blue Bottle Coffee",
                "description": "BLUE BOTTLE COFFEE",
                "plaid_raw_category": "FOOD_AND_DRINK",
                "plaid_raw_category_detailed": "FOOD_AND_DRINK_COFFEE",
                "pending": False,
            }
        ],
        "modified": [],
        "removed": [],
        "cursor": "cursor-1",
    }
    _connect_account(client, monkeypatch, first_sync_page)

    response = client.get("/api/transactions", params={"search": "blue bottle"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["category_name"] == "Coffee"
    assert results[0]["account_name"] == "Plaid Checking"

    assert client.get("/api/transactions", params={"search": "nonexistent"}).json() == []
