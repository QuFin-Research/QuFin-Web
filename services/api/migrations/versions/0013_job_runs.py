"""job runs: one row per data refresh, for the admin panel

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-17 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "job_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("requested_by", sa.String(length=254), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("steps_json", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_runs_started", "job_runs", ["started_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_job_runs_started", table_name="job_runs")
    op.drop_table("job_runs")
