"""score snapshots: the live scores as they were shown (rule 20)

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-19 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "score_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("scorecard_version", sa.String(length=16), nullable=False),
        sa.Column("catalog_version", sa.String(length=16), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_score_snapshots_lookup",
        "score_snapshots",
        ["code", "as_of", "payload_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_score_snapshots_lookup", table_name="score_snapshots")
    op.drop_table("score_snapshots")
