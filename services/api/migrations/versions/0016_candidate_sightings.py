"""candidate sightings: when each period of a staged candidate was first read (rule 38)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-20 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "candidate_sightings",
        sa.Column("series_id", sa.String(length=64), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("first_seen", sa.Date(), nullable=False),
        sa.Column("bootstrap", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("series_id", "period"),
    )
    op.create_index(
        "ix_candidate_sightings_series",
        "candidate_sightings",
        ["series_id", "first_seen"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_candidate_sightings_series", table_name="candidate_sightings")
    op.drop_table("candidate_sightings")
