"""Exercises the Plaid Link -> exchange -> accounts flow against fixture
data shaped like a real Plaid sandbox response, since we don't have live
Plaid credentials in this environment. This is what to re-run (or trust)
once real sandbox keys are in .env and the Link flow has been driven once
in a browser.
"""
from app import plaid_client, security
from app.models import Account, PlaidItem

FAKE_ACCOUNTS = [
    {
        "plaid_account_id": "acc_checking_1",
        "name": "Plaid Checking",
        "official_name": "Plaid Gold Standard 0% Interest Checking",
        "type": "depository",
        "subtype": "checking",
        "mask": "0000",
        "current_balance": 110.94,
        "available_balance": 100.0,
        "currency": "USD",
    },
    {
        "plaid_account_id": "acc_credit_1",
        "name": "Plaid Credit Card",
        "official_name": "Plaid Diamond 12.5% APR Interest Credit Card",
        "type": "credit",
        "subtype": "credit card",
        "mask": "3333",
        "current_balance": 410.0,
        "available_balance": None,
        "currency": "USD",
    },
]


def test_exchange_creates_item_and_accounts(client, db_session, monkeypatch):
    monkeypatch.setattr(
        plaid_client,
        "exchange_public_token",
        lambda public_token: {"access_token": "access-sandbox-abc123", "item_id": "item-abc123"},
    )
    monkeypatch.setattr(
        plaid_client,
        "get_accounts",
        lambda access_token: (FAKE_ACCOUNTS, "Fake Bank"),
    )

    response = client.post("/api/plaid/exchange", json={"public_token": "public-sandbox-xyz"})
    assert response.status_code == 200
    body = response.json()
    assert body["institution_name"] == "Fake Bank"
    assert body["accounts_added"] == 2

    item = db_session.query(PlaidItem).one()
    assert item.institution_name == "Fake Bank"
    # access token must be encrypted at rest, not stored in plaintext
    assert item.access_token != "access-sandbox-abc123"
    assert security.decrypt(item.access_token) == "access-sandbox-abc123"

    accounts = db_session.query(Account).order_by(Account.id).all()
    assert [a.plaid_account_id for a in accounts] == ["acc_checking_1", "acc_credit_1"]
    assert accounts[0].current_balance == 110.94
    assert accounts[1].type == "credit"


def test_accounts_endpoint_returns_stored_accounts(client, db_session, monkeypatch):
    monkeypatch.setattr(
        plaid_client,
        "exchange_public_token",
        lambda public_token: {"access_token": "access-sandbox-def456", "item_id": "item-def456"},
    )
    monkeypatch.setattr(
        plaid_client,
        "get_accounts",
        lambda access_token: (FAKE_ACCOUNTS[:1], "Fake Bank"),
    )
    client.post("/api/plaid/exchange", json={"public_token": "public-sandbox-xyz"})

    response = client.get("/api/accounts")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 1
    assert accounts[0]["name"] == "Plaid Checking"
    assert accounts[0]["institution_name"] == "Fake Bank"


def test_link_token_without_credentials_returns_503(client, monkeypatch):
    monkeypatch.setattr("app.config.PLAID_CLIENT_ID", "")
    monkeypatch.setattr("app.config.PLAID_SECRET", "")
    monkeypatch.setattr(plaid_client, "_client", None)

    response = client.post("/api/plaid/link-token")
    assert response.status_code == 503
