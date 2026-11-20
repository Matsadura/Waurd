"""Fill the database `perks` table from the engine's catalog.csv.

The CSV (backend/game/perks/catalog.csv) is where perks are added and
changed; this copies it into the table that the perks API and loadouts use.
It runs when the app starts and from scripts/import_perks.py.

- Rows are matched by id: new ids are inserted, existing ones updated.
- status "ready" in the CSV becomes is_enabled in the table.
- A perk removed from the CSV is disabled, not deleted, because loadouts and
  achievements may still point at it.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.game.config import GlyphType
from backend.game.perks import (
    PerkDefinition,
    PerkSpec,
    check_catalog,
    load_catalog,
    registered,
)
from backend.models.perk import ModificationType, Perk, Rarity, TargetGlyphType

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"{len(self.created)} created, {len(self.updated)} updated, "
            f"{len(self.disabled)} disabled"
        )


def _target(spec: PerkSpec) -> TargetGlyphType:
    if spec.targets == {GlyphType.POWER, GlyphType.SKILL}:
        return TargetGlyphType.ANY
    (only,) = spec.targets
    return TargetGlyphType(only.value)


def _columns(spec: PerkSpec, definition: PerkDefinition) -> dict[str, Any]:
    return {
        "name": spec.name,
        "description": spec.description,
        "quote": spec.quote,
        "image_url": spec.image,
        "rarity": Rarity(spec.rarity.value),
        "target_glyph_type": _target(spec),
        "modification_type": ModificationType(definition.kind.value),
        "durability": spec.durability,
        "is_enabled": spec.ready,
    }


async def import_perks(
    session: AsyncSession,
    catalog: Mapping[str, PerkSpec] | None = None,
) -> ImportReport:
    """Bring the perks table in line with the catalog. Flushes; the caller
    commits. Raises ValueError if a row has no perk function or the reverse."""
    catalog = load_catalog() if catalog is None else catalog
    definitions = registered()
    check_catalog(catalog, definitions)

    report = ImportReport()
    existing = {perk.id: perk for perk in (await session.scalars(select(Perk))).all()}
    for perk_id, spec in catalog.items():
        columns = _columns(spec, definitions[perk_id])
        perk = existing.get(perk_id)
        if perk is None:
            # The perk's logic is its Python function, so the old JSON rule
            # column is left empty.
            session.add(Perk(id=perk_id, effect_payload={}, **columns))
            report.created.append(perk_id)
            continue
        changed = False
        for name, value in columns.items():
            if getattr(perk, name) != value:
                setattr(perk, name, value)
                changed = True
        if changed:
            report.updated.append(perk_id)

    for perk_id, perk in existing.items():
        if perk_id not in catalog and perk.is_enabled:
            perk.is_enabled = False
            report.disabled.append(perk_id)

    await session.flush()
    return report


async def import_perks_on_startup(session: AsyncSession) -> None:
    """Run the import at app start. A failure is logged, not raised, so a
    database that isn't migrated yet doesn't stop the app from starting."""
    try:
        report = await import_perks(session)
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Importing perks from catalog.csv failed")
        return
    logger.info("Perks imported from catalog.csv: %s", report)
