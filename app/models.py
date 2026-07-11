import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PlaidItemStatus(str, enum.Enum):
    ACTIVE = "active"
    LOGIN_REQUIRED = "login_required"
    ERROR = "error"


class AccountType(str, enum.Enum):
    DEPOSITORY = "depository"
    CREDIT = "credit"
    LOAN = "loan"
    INVESTMENT = "investment"


class CategoryRuleMatchType(str, enum.Enum):
    MERCHANT_EXACT = "merchant_exact"
    MERCHANT_CONTAINS = "merchant_contains"
    PLAID_CATEGORY_EQUALS = "plaid_category_equals"


class InvestmentTransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    FEE = "fee"
    TRANSFER = "transfer"


class PlaidItem(Base):
    __tablename__ = "plaid_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plaid_item_id: Mapped[str] = mapped_column(String, unique=True)
    institution_name: Mapped[str] = mapped_column(String)
    access_token: Mapped[str] = mapped_column(String)  # Fernet-encrypted at rest
    sync_cursor: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[PlaidItemStatus] = mapped_column(
        String, default=PlaidItemStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    accounts: Mapped[list["Account"]] = relationship(back_populates="item")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("plaid_items.id"))
    plaid_account_id: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    official_name: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[AccountType] = mapped_column(String)
    subtype: Mapped[str | None] = mapped_column(String, nullable=True)
    mask: Mapped[str | None] = mapped_column(String, nullable=True)
    current_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    available_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    currency: Mapped[str] = mapped_column(String, default="USD")

    item: Mapped["PlaidItem"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    holdings: Mapped[list["Holding"]] = relationship(back_populates="account")
    investment_transactions: Mapped[list["InvestmentTransaction"]] = relationship(
        back_populates="account"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    group: Mapped[str | None] = mapped_column(String, nullable=True)
    parent_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)

    parent: Mapped["Category | None"] = relationship(remote_side=[id])


class CategoryRule(Base):
    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_type: Mapped[CategoryRuleMatchType] = mapped_column(String)
    match_value: Mapped[str] = mapped_column(String)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    created_from_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped["Category"] = relationship()


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    plaid_transaction_id: Mapped[str] = mapped_column(String, unique=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)  # Plaid convention: positive = money out
    merchant_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    plaid_raw_category: Mapped[str | None] = mapped_column(String, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    pending: Mapped[bool] = mapped_column(Boolean, default=False)
    is_manually_recategorized: Mapped[bool] = mapped_column(Boolean, default=False)

    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship()


class Security(Base):
    __tablename__ = "securities"

    id: Mapped[int] = mapped_column(primary_key=True)
    plaid_security_id: Mapped[str] = mapped_column(String, unique=True)
    ticker_symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    security_type: Mapped[str | None] = mapped_column(String, nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_price_as_of: Mapped[date | None] = mapped_column(Date, nullable=True)

    holdings: Mapped[list["Holding"]] = relationship(back_populates="security")


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("account_id", "security_id", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    snapshot_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[float] = mapped_column(Float)
    cost_basis: Mapped[float | None] = mapped_column(Float, nullable=True)
    institution_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    institution_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="holdings")
    security: Mapped["Security"] = relationship(back_populates="holdings")


class InvestmentTransaction(Base):
    __tablename__ = "investment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    security_id: Mapped[int | None] = mapped_column(
        ForeignKey("securities.id"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date)
    type: Mapped[InvestmentTransactionType] = mapped_column(String)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="investment_transactions")
    security: Mapped["Security | None"] = relationship()


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, unique=True)
    total_assets: Mapped[float] = mapped_column(Float)
    total_liabilities: Mapped[float] = mapped_column(Float)
    net_worth: Mapped[float] = mapped_column(Float)
    breakdown_json: Mapped[str | None] = mapped_column(String, nullable=True)


class BudgetTarget(Base):
    __tablename__ = "budget_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    month: Mapped[str | None] = mapped_column(String, nullable=True)  # "YYYY-MM", null = recurring
    target_amount: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship()
