"""macro query indexes and stored series coverage

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-01 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.add_column(sa.Column("first_period", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("last_period", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("vintage_rows", sa.Integer(), nullable=False, server_default="0")
        )
    # Backfill coverage once, so listing series no longer aggregates every observation.
    op.execute(
        """
        UPDATE macro_series SET
            first_period = (SELECT min(period) FROM macro_observations o
                            WHERE o.series_id = macro_series.id),
            last_period = (SELECT max(period) FROM macro_observations o
                           WHERE o.series_id = macro_series.id),
            vintage_rows = (SELECT count(*) FROM macro_observations o
                            WHERE o.series_id = macro_series.id)
        """
    )
    op.create_index(
        "ix_macro_observations_asof_end",
        "macro_observations",
        ["series_id", "realtime_end", "period"],
    )
    op.create_index(
        "ix_macro_observations_period",
        "macro_observations",
        ["period", "series_id", "realtime_start"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_macro_observations_period", table_name="macro_observations")
    op.drop_index("ix_macro_observations_asof_end", table_name="macro_observations")
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.drop_column("vintage_rows")
        batch_op.drop_column("last_period")
        batch_op.drop_column("first_period")
