"""add user role

Revision ID: 8f3c2a1d9b7e
Revises: 299c9da9deb1
Create Date: 2026-11-16 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f3c2a1d9b7e"
down_revision: Union[str, Sequence[str], None] = "299c9da9deb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Every existing user becomes a normal USER."""
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("USER", "GAME_MASTER", name="userrole"),
            server_default="USER",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
