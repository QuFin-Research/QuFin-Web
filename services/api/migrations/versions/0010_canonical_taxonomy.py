"""canonical taxonomy: series code, pillar and scale, and the country dimension (ADR 0007)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.data.taxonomy import canonical_code, pillar_for, scale_of

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.add_column(sa.Column("canonical_code", sa.String(length=96), nullable=True))
        batch_op.add_column(sa.Column("pillar", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column("scale", sa.Float(), nullable=False, server_default=sa.text("1"))
        )
    # Backfill from each stored series' own metadata; every later ingest derives it again.
    conn = op.get_bind()
    series = sa.table(
        "macro_series",
        sa.column("id", sa.String),
        sa.column("country", sa.String),
        sa.column("frequency", sa.String),
        sa.column("seasonal_adjustment", sa.String),
        sa.column("units", sa.String),
        sa.column("canonical_code", sa.String),
        sa.column("pillar", sa.String),
        sa.column("scale", sa.Float),
    )
    rows = conn.execute(
        sa.select(
            series.c.id,
            series.c.country,
            series.c.frequency,
            series.c.seasonal_adjustment,
            series.c.units,
        )
    ).all()
    for row in rows:
        conn.execute(
            series.update()
            .where(series.c.id == row.id)
            .values(
                canonical_code=canonical_code(
                    row.id, row.country, row.frequency, row.seasonal_adjustment
                ),
                pillar=pillar_for(row.country, row.id),
                scale=scale_of(row.units),
            )
        )
    op.create_index(
        "ix_macro_series_canonical_code", "macro_series", ["canonical_code"], unique=True
    )
    op.create_index("ix_macro_series_pillar", "macro_series", ["pillar"])

    op.create_table(
        "dim_country_taxonomy",
        sa.Column("iso3", sa.String(length=3), nullable=False),
        sa.Column("iso2", sa.String(length=2), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("central_bank", sa.Text(), nullable=False),
        sa.Column("g7", sa.Boolean(), nullable=False),
        sa.Column("g20", sa.Boolean(), nullable=False),
        sa.Column("gcc", sa.Boolean(), nullable=False),
        sa.Column("em", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("iso3"),
        sa.UniqueConstraint("iso2"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("dim_country_taxonomy")
    op.drop_index("ix_macro_series_pillar", table_name="macro_series")
    op.drop_index("ix_macro_series_canonical_code", table_name="macro_series")
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.drop_column("scale")
        batch_op.drop_column("pillar")
        batch_op.drop_column("canonical_code")
