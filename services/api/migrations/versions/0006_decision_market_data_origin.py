"""decision market data origin

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-01 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Every decision logged so far was logged on sample data.
    with op.batch_alter_table("decisions") as batch_op:
        batch_op.add_column(
            sa.Column("market_data", sa.String(length=8), nullable=False, server_default="sample")
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("decisions") as batch_op:
        batch_op.drop_column("market_data")
