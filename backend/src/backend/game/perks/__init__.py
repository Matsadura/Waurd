"""Perks: the CSV catalog, one function per perk, and the shared rules.

Importing this package registers every perk in builtin.py.
"""

from backend.game.perks import builtin as _builtin  # noqa: F401  (registers perks)
from backend.game.perks.apply import (
    PerkError,
    PerkProblem,
    PerkResult,
    apply_perk,
    check_catalog,
    grant_perk,
)
from backend.game.perks.catalog import CatalogError, PerkSpec, load_catalog
from backend.game.perks.registry import (
    PerkContext,
    PerkDefinition,
    PerkKind,
    conditional_rules,
    registered,
)

__all__ = [
    "CatalogError",
    "PerkContext",
    "PerkDefinition",
    "PerkError",
    "PerkKind",
    "PerkProblem",
    "PerkResult",
    "PerkSpec",
    "apply_perk",
    "check_catalog",
    "conditional_rules",
    "grant_perk",
    "load_catalog",
    "registered",
]
