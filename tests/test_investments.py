from datetime import date

from app import plaid_client
from app.models import Holding, InvestmentTransaction, Security

ACCOUNTS = [
    {
        "plaid_account_id": "acc_brokerage_1",
        "name": "Brokerage",
        "official_name": None,
        "type": "investment",
        "subtype": "brokerage",
        "mask": None,
        "current_balance": 2500.0,
        "available_balance": None,
        "currency": "USD",
    }
]

SECURITIES = [
    {
        "plaid_security_id": "sec_voo",
        "ticker_symbol": "VOO",
        "name": "Vanguard S&P 500 ETF",
        "security_type": "etf",
        "close_price": 250.0,
        "close_price_as_of": date.today(),
    }
]

HOLDINGS = [
    {
        "account_id": "acc_brokerage_1",
        "security_id": "sec_voo",
        "quantity": 10.0,
        "cost_basis": 2000.0,
        "institution_price": 250.0,
        "institution_value": 2500.0,
    }
]

INVESTMENT_TRANSACTIONS = [
    {
        "plaid_investment_transaction_id": "invtx_1",
        "account_id": "acc_brokerage_1",
        "security_id": "sec_voo",
        "date": date.today(),
        "type": "buy",
        "quantity": 10.0,
        "price": 200.0,
        "amount": 2000.0,
        "name": "Buy VOO",
    }
]


def _connect_brokerage(client, monkeypatch):
    monkeypatch.setattr(
        plaid_client,
        "exchange_public_token",
        lambda public_token: {"access_token": "access-sandbox-inv", "item_id": "item-inv"},
    )
    monkeypatch.setattr(plaid_client, "get_accounts", lambda access_token: (ACCOUNTS, "Fake Brokerage"))
    monkeypatch.setattr(
        plaid_client,
        "sync_transactions",
        lambda access_token, cursor: {"added": [], "modified": [], "removed": [], "cursor": None},
    )
    monkeypatch.setattr(
        plaid_client,
        "get_investment_holdings",
        lambda access_token: {"holdings": HOLDINGS, "securities": SECURITIES},
    )
    monkeypatch.setattr(
        plaid_client,
        "get_investment_transactions",
        lambda access_token, start_date, end_date: {
            "investment_transactions": INVESTMENT_TRANSACTIONS,
            "securities": SECURITIES,
        },
    )
    return client.post("/api/plaid/exchange", json={"public_token": "public-sandbox-inv"})


def test_backfill_creates_security_holding_and_investment_transaction(client, db_session, monkeypatch):
    response = _connect_brokerage(client, monkeypatch)
    assert response.status_code == 200

    security_row = db_session.query(Security).one()
    assert security_row.ticker_symbol == "VOO"

    holding = db_session.query(Holding).one()
    assert holding.quantity == 10.0
    assert holding.institution_value == 2500.0

    investment_transaction = db_session.query(InvestmentTransaction).one()
    assert investment_transaction.plaid_investment_transaction_id == "invtx_1"
    assert investment_transaction.type == "buy"


def test_holdings_endpoint_computes_gain_loss(client, db_session, monkeypatch):
    _connect_brokerage(client, monkeypatch)

    response = client.get("/api/investments/holdings")
    assert response.status_code == 200
    holdings = response.json()
    assert len(holdings) == 1
    assert holdings[0]["ticker_symbol"] == "VOO"
    assert holdings[0]["gain_loss"] == 500.0
    assert holdings[0]["gain_loss_pct"] == 0.25


def test_performance_endpoint_returns_allocation(client, db_session, monkeypatch):
    _connect_brokerage(client, monkeypatch)

    response = client.get("/api/investments/performance")
    assert response.status_code == 200
    body = response.json()
    assert body["allocation"] == {"etf": 2500.0}
    assert body["total_value"] == 2500.0
    assert body["total_cost_basis"] == 2000.0
    assert body["total_gain_loss"] == 500.0


def test_transactions_endpoint_returns_investment_activity(client, db_session, monkeypatch):
    _connect_brokerage(client, monkeypatch)

    response = client.get("/api/investments/transactions")
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["ticker_symbol"] == "VOO"
    assert transactions[0]["type"] == "buy"


def test_resync_is_idempotent(client, db_session, monkeypatch):
    response = _connect_brokerage(client, monkeypatch)
    item_id = response.json()["item_id"]

    sync_response = client.post(f"/api/plaid/items/{item_id}/sync")
    assert sync_response.status_code == 200

    assert db_session.query(Security).count() == 1
    assert db_session.query(Holding).count() == 1
    assert db_session.query(InvestmentTransaction).count() == 1
