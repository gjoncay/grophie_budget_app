"""Centralizes every Plaid SDK call. Callers pass/receive plain Python
primitives — nobody outside this module touches a Plaid model object.
"""
from datetime import date

import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import (
    InvestmentsTransactionsGetRequest,
)
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from app import config

_ENV_HOSTS = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


class PlaidNotConfigured(RuntimeError):
    pass


_client: plaid_api.PlaidApi | None = None


def _get_client() -> plaid_api.PlaidApi:
    global _client
    if _client is not None:
        return _client
    if not config.PLAID_CLIENT_ID or not config.PLAID_SECRET:
        raise PlaidNotConfigured(
            "PLAID_CLIENT_ID / PLAID_SECRET are not set. Create a free developer "
            "account at https://dashboard.plaid.com and add them to .env."
        )
    configuration = plaid.Configuration(
        host=_ENV_HOSTS.get(config.PLAID_ENV, plaid.Environment.Sandbox),
        api_key={"clientId": config.PLAID_CLIENT_ID, "secret": config.PLAID_SECRET},
    )
    _client = plaid_api.PlaidApi(plaid.ApiClient(configuration))
    return _client


def create_link_token() -> str:
    request = LinkTokenCreateRequest(
        client_name="Hearth",
        language="en",
        country_codes=[CountryCode("US")],
        user=LinkTokenCreateRequestUser(client_user_id="hearth-household"),
        products=[Products("transactions"), Products("investments")],
    )
    response = _get_client().link_token_create(request)
    return response.link_token


def exchange_public_token(public_token: str) -> dict:
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = _get_client().item_public_token_exchange(request)
    return {"access_token": response.access_token, "item_id": response.item_id}


def get_accounts(access_token: str) -> list[dict]:
    request = AccountsGetRequest(access_token=access_token)
    response = _get_client().accounts_get(request)
    item = response.item
    return [
        {
            "plaid_account_id": a.account_id,
            "name": a.name,
            "official_name": a.official_name,
            "type": a.type.value,
            "subtype": a.subtype.value if a.subtype else None,
            "mask": a.mask,
            "current_balance": a.balances.current,
            "available_balance": a.balances.available,
            "currency": a.balances.iso_currency_code or "USD",
        }
        for a in response.accounts
    ], item.institution_name or "Unknown institution"


def sync_transactions(access_token: str, cursor: str | None) -> dict:
    added, modified, removed = [], [], []
    has_more = True
    while has_more:
        request = TransactionsSyncRequest(access_token=access_token, cursor=cursor)
        response = _get_client().transactions_sync(request)
        added.extend(_serialize_transaction(t) for t in response.added)
        modified.extend(_serialize_transaction(t) for t in response.modified)
        removed.extend(t.transaction_id for t in response.removed)
        cursor = response.next_cursor
        has_more = response.has_more
    return {"added": added, "modified": modified, "removed": removed, "cursor": cursor}


def _serialize_transaction(t) -> dict:
    return {
        "plaid_transaction_id": t.transaction_id,
        "account_id": t.account_id,
        "date": t.date,
        "amount": t.amount,
        "merchant_name": t.merchant_name,
        "description": t.name,
        "plaid_raw_category": t.personal_finance_category.primary
        if t.personal_finance_category
        else None,
        "plaid_raw_category_detailed": t.personal_finance_category.detailed
        if t.personal_finance_category
        else None,
        "pending": t.pending,
    }


def get_investment_holdings(access_token: str) -> dict:
    request = InvestmentsHoldingsGetRequest(access_token=access_token)
    response = _get_client().investments_holdings_get(request)
    holdings = [
        {
            "account_id": h.account_id,
            "security_id": h.security_id,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "institution_price": h.institution_price,
            "institution_value": h.institution_value,
        }
        for h in response.holdings
    ]
    securities = [_serialize_security(s) for s in response.securities]
    return {"holdings": holdings, "securities": securities}


def _serialize_security(s) -> dict:
    return {
        "plaid_security_id": s.security_id,
        "ticker_symbol": s.ticker_symbol,
        "name": s.name,
        "security_type": s.type,
        "close_price": s.close_price,
        "close_price_as_of": s.close_price_as_of,
    }


def get_investment_transactions(
    access_token: str, start_date: date, end_date: date
) -> dict:
    request = InvestmentsTransactionsGetRequest(
        access_token=access_token, start_date=start_date, end_date=end_date
    )
    response = _get_client().investments_transactions_get(request)
    transactions = [
        {
            "plaid_investment_transaction_id": t.investment_transaction_id,
            "account_id": t.account_id,
            "security_id": t.security_id,
            "date": t.date,
            "type": t.type.value,
            "quantity": t.quantity,
            "price": t.price,
            "amount": t.amount,
            "name": t.name,
        }
        for t in response.investment_transactions
    ]
    securities = [_serialize_security(s) for s in response.securities]
    return {"investment_transactions": transactions, "securities": securities}


def remove_item(access_token: str) -> None:
    _get_client().item_remove(ItemRemoveRequest(access_token=access_token))
