"""Perks: the CSV catalog, one function per perk, and the shared rules."""

from backend.game.perks.catalog import CATALOG
from backend.game.perks.effects import BONUS, DIRECT

_missing = sorted(set(CATALOG) - set(DIRECT) - set(BONUS))
_extra = sorted((set(DIRECT) | set(BONUS)) - set(CATALOG))
if _missing or _extra or set(DIRECT) & set(BONUS):
    raise RuntimeError(
        f"catalog.csv and effects.py disagree: no function for {_missing}, "
        f"no row for {_extra}"
    )
