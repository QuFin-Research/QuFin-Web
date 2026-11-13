"""economic calendar: release date, previous, consensus, actual and surprise (ADR 0007)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-12 12:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "fact_economic_calendar",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.String(length=64), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("release_time_utc", sa.Time(), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("previous_value", sa.Float(), nullable=True),
        sa.Column("consensus_estimate", sa.Float(), nullable=True),
        sa.Column("consensus_source", sa.String(length=120), nullable=True),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("surprise_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["series_id"], ["macro_series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "period", name="uq_calendar_series_period"),
    )
    op.create_index(
        "ix_calendar_release_date", "fact_economic_calendar", ["release_date", "series_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_calendar_release_date", table_name="fact_economic_calendar")
    op.drop_table("fact_economic_calendar")
