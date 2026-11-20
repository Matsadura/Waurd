"""The perk catalog: catalog.csv, exported from the team's perk sheet
(https://docs.google.com/spreadsheets/d/1_cI2TWjNddDOus2dvGEwRkRAADtAO70mfKFFKJH2gts).

Each row describes a perk; its behaviour is the Python function registered
under the row's id (see registry.py). The database `perks` table is filled
from this file by backend.core.perk_import, so the CSV is the one place a
perk's name, rarity, durability and so on are changed.
"""

import csv
import io
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

from backend.game.config import GlyphType, Rarity

COLUMNS = (
    "id",
    "name",
    "rarity",
    "description",
    "mechanics",
    "image",
    "durability",
    "quote",
    "target_type",
    "status",
)
MAX_ID = 32
MAX_NAME = 20
MAX_DESCRIPTION = 120
MAX_QUOTE = 120
MAX_IMAGE = 255
READY = "ready"
NOT_READY = "not_ready"

_ID = re.compile(r"[a-z0-9_]+")


class CatalogError(ValueError):
    """The CSV has a row the game can't use; the message names the row."""


@dataclass(frozen=True, slots=True)
class PerkSpec:
    """One catalog row. durability None means unlimited."""

    id: str
    name: str
    rarity: Rarity
    description: str
    mechanics: str
    image: str | None
    durability: int | None
    quote: str | None
    targets: frozenset[GlyphType]
    ready: bool

    def supports(self, glyph_type: GlyphType) -> bool:
        return glyph_type in self.targets


def _text(row: Mapping[str, str | None], column: str) -> str:
    return (row.get(column) or "").strip()


def _row(line: int, row: Mapping[str, str | None]) -> PerkSpec:
    def fail(message: str) -> CatalogError:
        return CatalogError(f"catalog.csv line {line}: {message}")

    perk_id = _text(row, "id")
    if not _ID.fullmatch(perk_id) or len(perk_id) > MAX_ID:
        raise fail(f"id {perk_id!r} must be 1-{MAX_ID} of a-z, 0-9 and _.")

    name = _text(row, "name")
    if not 1 <= len(name) <= MAX_NAME:
        raise fail(f"name must be 1-{MAX_NAME} characters.")
    description = _text(row, "description")
    if not 1 <= len(description) <= MAX_DESCRIPTION:
        raise fail(f"description must be 1-{MAX_DESCRIPTION} characters.")
    quote = _text(row, "quote") or None
    if quote is not None and len(quote) > MAX_QUOTE:
        raise fail(f"quote must be at most {MAX_QUOTE} characters.")
    image = _text(row, "image") or None
    if image is not None and len(image) > MAX_IMAGE:
        raise fail(f"image must be at most {MAX_IMAGE} characters.")

    try:
        rarity = Rarity(_text(row, "rarity").upper())
    except ValueError:
        raise fail(
            f"rarity {_text(row, 'rarity')!r} must be common, uncommon, rare or "
            "legendary."
        ) from None

    raw_durability = _text(row, "durability")
    durability: int | None = None
    if raw_durability:
        if not raw_durability.isdigit() or int(raw_durability) < 1:
            raise fail("durability must be empty (unlimited) or a whole number >= 1.")
        durability = int(raw_durability)

    targets: set[GlyphType] = set()
    for part in _text(row, "target_type").split(","):
        try:
            targets.add(GlyphType(part.strip().upper()))
        except ValueError:
            raise fail(
                f"target_type {_text(row, 'target_type')!r} must be power, "
                "skill or both."
            ) from None

    status = _text(row, "status")
    if status not in (READY, NOT_READY):
        raise fail(f"status must be {READY} or {NOT_READY}.")

    return PerkSpec(
        id=perk_id,
        name=name,
        rarity=rarity,
        description=description,
        mechanics=_text(row, "mechanics"),
        image=image,
        durability=durability,
        quote=quote,
        targets=frozenset(targets),
        ready=status == READY,
    )


def parse_catalog(text: str) -> dict[str, PerkSpec]:
    """Read catalog CSV text into specs by id. Raises CatalogError."""
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise CatalogError(f"catalog.csv columns must be: {', '.join(COLUMNS)}.")
    catalog: dict[str, PerkSpec] = {}
    for row in reader:
        spec = _row(reader.line_num, row)
        if spec.id in catalog:
            raise CatalogError(
                f"catalog.csv line {reader.line_num}: id {spec.id} appears twice."
            )
        catalog[spec.id] = spec
    return catalog


@lru_cache(maxsize=1)
def load_catalog() -> Mapping[str, PerkSpec]:
    """The bundled catalog.csv. Cached, so it's read once per process."""
    text = (
        resources.files("backend.game.perks")
        .joinpath("catalog.csv")
        .read_text(encoding="utf-8")
    )
    return parse_catalog(text)
