"""make_player2_id_nullable_and_add_invite_code

Revision ID: 299c9da9deb1
Revises: 15d8ff8d3f1a
Create Date: 2026-11-09 23:56:26.751731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '299c9da9deb1'
down_revision: Union[str, Sequence[str], None] = '15d8ff8d3f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Manually added: modify player2_id to allow NULL values
    op.alter_column(
        'matches',
        'player2_id',
        existing_type=sa.BINARY(length=16),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'matches',
        'player2_id',
        existing_type=sa.BINARY(length=16),
        nullable=False,
    )
