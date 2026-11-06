"""unit kind and currency of every macro series (rule 23)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-07 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.domain.units import classify

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.add_column(sa.Column("unit_kind", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("currency", sa.String(length=3), nullable=True))
    # Backfill from each stored series' own units text; every later ingest derives it again.
    conn = op.get_bind()
    series = sa.table(
        "macro_series",
        sa.column("id", sa.String),
        sa.column("units", sa.String),
        sa.column("country", sa.String),
        sa.column("unit_kind", sa.String),
        sa.column("currency", sa.String),
    )
    for row in conn.execute(sa.select(series.c.id, series.c.units, series.c.country)).all():
        unit = classify(row.units, row.country)
        conn.execute(
            series.update()
            .where(series.c.id == row.id)
            .values(unit_kind=unit.kind, currency=unit.currency)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.drop_column("currency")
        batch_op.drop_column("unit_kind")
