"""CFTC Traders in Financial Futures reports

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-05 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Financial contracts now read from this report; their legacy rows would be the same
# positions stored twice (rule 16), so they are removed.
MOVED_TO_TFF = ("099741", "096742", "097741", "232741", "133741", "146021")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cot_financial_reports",
        sa.Column("contract_code", sa.String(length=8), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("market_name", sa.String(length=128), nullable=False),
        sa.Column("open_interest", sa.Integer(), nullable=False),
        sa.Column("dealer_long", sa.Integer(), nullable=False),
        sa.Column("dealer_short", sa.Integer(), nullable=False),
        sa.Column("dealer_spread", sa.Integer(), nullable=False),
        sa.Column("asset_mgr_long", sa.Integer(), nullable=False),
        sa.Column("asset_mgr_short", sa.Integer(), nullable=False),
        sa.Column("asset_mgr_spread", sa.Integer(), nullable=False),
        sa.Column("lev_money_long", sa.Integer(), nullable=False),
        sa.Column("lev_money_short", sa.Integer(), nullable=False),
        sa.Column("lev_money_spread", sa.Integer(), nullable=False),
        sa.Column("other_rept_long", sa.Integer(), nullable=False),
        sa.Column("other_rept_short", sa.Integer(), nullable=False),
        sa.Column("other_rept_spread", sa.Integer(), nullable=False),
        sa.Column("nonrept_long", sa.Integer(), nullable=False),
        sa.Column("nonrept_short", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("contract_code", "report_date"),
    )
    with op.batch_alter_table("cot_financial_reports", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_cot_financial_reports_release_date"), ["release_date"], unique=False
        )
    cot = sa.table("cot_reports", sa.column("contract_code", sa.String))
    op.execute(cot.delete().where(cot.c.contract_code.in_(MOVED_TO_TFF)))


def downgrade() -> None:
    """Downgrade schema. Legacy rows for the moved contracts come back on the next ingest."""
    with op.batch_alter_table("cot_financial_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_cot_financial_reports_release_date"))
    op.drop_table("cot_financial_reports")
