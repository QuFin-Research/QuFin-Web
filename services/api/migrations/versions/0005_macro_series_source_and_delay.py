"""macro series source, release and FRED delay notice

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.add_column(sa.Column("source_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("release_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("delay_notice", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("macro_series") as batch_op:
        batch_op.drop_column("delay_notice")
        batch_op.drop_column("release_name")
        batch_op.drop_column("source_name")
