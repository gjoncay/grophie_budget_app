"""add plaid investment transaction id

Revision ID: b7438ad6c0b4
Revises: c164d8e04ba7
Create Date: 2026-07-10 17:03:14.120259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7438ad6c0b4'
down_revision: Union[str, Sequence[str], None] = 'c164d8e04ba7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("investment_transactions") as batch_op:
        batch_op.add_column(sa.Column("plaid_investment_transaction_id", sa.String(), nullable=False))
        batch_op.create_unique_constraint(
            "uq_investment_transactions_plaid_id", ["plaid_investment_transaction_id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("investment_transactions") as batch_op:
        batch_op.drop_constraint("uq_investment_transactions_plaid_id", type_="unique")
        batch_op.drop_column("plaid_investment_transaction_id")
