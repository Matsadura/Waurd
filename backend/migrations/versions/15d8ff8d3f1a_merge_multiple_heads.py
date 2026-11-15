"""merge_multiple_heads

Revision ID: 15d8ff8d3f1a
Revises: 5500391f6cad, d7b1f8a2c4e6
Create Date: 2026-11-09 23:55:43.719246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15d8ff8d3f1a'
down_revision: Union[str, Sequence[str], None] = ('5500391f6cad', 'd7b1f8a2c4e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
