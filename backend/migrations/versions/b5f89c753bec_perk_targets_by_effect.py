"""perk targets by effect

Revision ID: b5f89c753bec
Revises: c22c943ff2b5
Create Date: 2026-11-27 16:33:44.965814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'b5f89c753bec'
down_revision: Union[str, Sequence[str], None] = 'c22c943ff2b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD = ("POWER", "SKILL", "ANY")
NEW = ("DAMAGE", "HEAL_DEFENSE", "ANY")
BOTH = ("POWER", "SKILL", "DAMAGE", "HEAL_DEFENSE", "ANY")


def _retype(values: tuple[str, ...]) -> None:
    op.alter_column(
        "perks",
        "target_glyph_type",
        existing_type=mysql.ENUM(*BOTH),
        type_=sa.Enum(*values, name="targetglyphtype"),
        existing_nullable=False,
    )


def upgrade() -> None:
    """Targets by effect: the old POWER meant damage glyphs and SKILL heal or
    defense ones. Widen the type, move the rows, then narrow it."""
    _retype(BOTH)
    op.execute("UPDATE perks SET target_glyph_type = 'DAMAGE' WHERE target_glyph_type = 'POWER'")
    op.execute("UPDATE perks SET target_glyph_type = 'HEAL_DEFENSE' WHERE target_glyph_type = 'SKILL'")
    _retype(NEW)


def downgrade() -> None:
    _retype(BOTH)
    op.execute("UPDATE perks SET target_glyph_type = 'POWER' WHERE target_glyph_type = 'DAMAGE'")
    op.execute("UPDATE perks SET target_glyph_type = 'SKILL' WHERE target_glyph_type = 'HEAL_DEFENSE'")
    _retype(OLD)
