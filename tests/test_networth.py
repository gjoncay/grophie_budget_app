from datetime import date, datetime, timedelta

from app import networth
from app.models import Account, NetWorthSnapshot, PlaidItem, Transaction


def _make_item_and_account(db_session, account_type="depository", current_balance=100.0):
    item = PlaidItem(
        plaid_item_id="item-1",
        institution_name="Fake Bank",
        access_token="irrelevant-for-this-test",
    )
    db_session.add(item)
    db_session.flush()
    account = Account(
        item_id=item.id,
        plaid_account_id=f"acc-{account_type}",
        name="Test Account",
        type=account_type,
        current_balance=current_balance,
        currency="USD",
    )
    db_session.add(account)
    db_session.commit()
    return item, account


def test_reconstructed_balances_match_hand_computation(db_session):
    today = date.today()
    two_days_ago, one_day_ago = today - timedelta(days=2), today - timedelta(days=1)

    _, account = _make_item_and_account(db_session, current_balance=100.0)
    # spent $20 two days ago, received a $50 deposit yesterday, spent $10 today
    # (Plaid convention: positive amount = money out)
    db_session.add_all(
        [
            Transaction(
                account_id=account.id, plaid_transaction_id="t1", date=two_days_ago, amount=20.0
            ),
            Transaction(
                account_id=account.id, plaid_transaction_id="t2", date=one_day_ago, amount=-50.0
            ),
            Transaction(account_id=account.id, plaid_transaction_id="t3", date=today, amount=10.0),
        ]
    )
    db_session.commit()

    written = networth.recompute_net_worth_history(db_session)
    assert written == 3  # one snapshot per day from two_days_ago through today

    snapshots = {
        s.snapshot_date: s
        for s in db_session.query(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date).all()
    }
    assert snapshots[today].net_worth == 100.0
    assert snapshots[one_day_ago].net_worth == 110.0
    assert snapshots[two_days_ago].net_worth == 60.0


def test_liability_account_reduces_net_worth(db_session):
    today = date.today()
    _, checking = _make_item_and_account(db_session, "depository", current_balance=1000.0)
    item2 = PlaidItem(plaid_item_id="item-2", institution_name="Fake Bank", access_token="x")
    db_session.add(item2)
    db_session.flush()
    credit_card = Account(
        item_id=item2.id,
        plaid_account_id="acc-credit",
        name="Credit Card",
        type="credit",
        current_balance=300.0,
        currency="USD",
    )
    db_session.add(credit_card)
    # need at least one transaction for recompute to have a date range to work with
    db_session.add(
        Transaction(account_id=checking.id, plaid_transaction_id="t1", date=today, amount=5.0)
    )
    db_session.commit()

    networth.recompute_net_worth_history(db_session)
    snapshot = db_session.query(NetWorthSnapshot).filter_by(snapshot_date=today).one()
    assert snapshot.total_assets == 1000.0
    assert snapshot.total_liabilities == 300.0
    assert snapshot.net_worth == 700.0


def test_investment_balance_only_counts_from_connection_day_forward(db_session):
    today = date.today()
    fifteen_days_ago = today - timedelta(days=15)
    connected_date = today - timedelta(days=10)

    item = PlaidItem(plaid_item_id="item-inv", institution_name="Fake Brokerage", access_token="x")
    db_session.add(item)
    db_session.flush()
    checking = Account(
        item_id=item.id,
        plaid_account_id="acc-checking",
        name="Checking",
        type="depository",
        current_balance=100.0,
        currency="USD",
    )
    brokerage = Account(
        item_id=item.id,
        plaid_account_id="acc-brokerage",
        name="Brokerage",
        type="investment",
        current_balance=5000.0,
        currency="USD",
    )
    db_session.add_all([checking, brokerage])
    db_session.flush()
    # a zero-amount transaction just to establish the reconstruction window's
    # start date; checking's balance stays flat at 100 across the whole range
    db_session.add(
        Transaction(
            account_id=checking.id, plaid_transaction_id="t1", date=fifteen_days_ago, amount=0.0
        )
    )
    db_session.commit()

    item.created_at = datetime.combine(connected_date, datetime.min.time())
    db_session.commit()

    networth.recompute_net_worth_history(db_session)
    snapshots = {
        s.snapshot_date: s
        for s in db_session.query(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date).all()
    }

    before_connecting = fifteen_days_ago + timedelta(days=2)
    assert snapshots[before_connecting].total_assets == 100.0  # investment excluded

    assert snapshots[connected_date].total_assets == 5100.0  # investment included from this day
    assert snapshots[today].total_assets == 5100.0


def test_insight_compares_to_thirty_days_ago(db_session):
    today = date.today()
    db_session.add_all(
        [
            NetWorthSnapshot(
                snapshot_date=today - timedelta(days=31),
                total_assets=10000,
                total_liabilities=0,
                net_worth=10000,
            ),
            NetWorthSnapshot(
                snapshot_date=today, total_assets=11500, total_liabilities=0, net_worth=11500
            ),
        ]
    )
    db_session.commit()

    message = networth.build_insight(db_session)
    assert "up" in message
    assert "$1,500" in message


def test_insight_without_any_data(db_session):
    assert "Connect an account" in networth.build_insight(db_session)
