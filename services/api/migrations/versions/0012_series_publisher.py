"""canonical publisher of every macro series

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-12 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.data.publishers import canonical_publisher

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.add_column(sa.Column("publisher", sa.String(length=255), nullable=True))
    # Backfill from the producer's wording each series already stores; later ingests derive it.
    conn = op.get_bind()
    series = sa.table(
        "macro_series",
        sa.column("id", sa.String),
        sa.column("source_name", sa.String),
        sa.column("publisher", sa.String),
    )
    for row in conn.execute(sa.select(series.c.id, series.c.source_name)).all():
        conn.execute(
            series.update()
            .where(series.c.id == row.id)
            .values(publisher=canonical_publisher(row.source_name))
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.drop_column("publisher")
