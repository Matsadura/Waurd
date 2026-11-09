"""add oauth identity constraint

Revision ID: d7b1f8a2c4e6
Revises: c792f4d78b02
Create Date: 2026-11-01 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7b1f8a2c4e6"
down_revision: str | Sequence[str] | None = "c792f4d78b02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_users_oauth_provider_id",
        "users",
        ["oauth_provider", "oauth_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_oauth_provider_id", table_name="users")
