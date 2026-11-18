"""source decisions and series lifecycle (rules 16, P)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-18 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "source_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("concept", sa.String(length=64), nullable=False),
        sa.Column("series_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_decisions_pair",
        "source_decisions",
        ["country", "concept", "effective_from"],
        unique=False,
    )
    # live: served; retired: a pair's previous source, read only for as-of dates before the
    # change; staged: a candidate being timed, never served or scored.
    op.add_column(
        "macro_series",
        sa.Column("lifecycle", sa.String(length=8), server_default="live", nullable=False),
    )
    op.add_column("macro_series", sa.Column("retired_on", sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("macro_series", "retired_on")
    op.drop_column("macro_series", "lifecycle")
    op.drop_index("ix_source_decisions_pair", table_name="source_decisions")
    op.drop_table("source_decisions")
