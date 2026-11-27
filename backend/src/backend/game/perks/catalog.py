"""The perk catalog: catalog.csv, exported from the team's perk sheet
(https://docs.google.com/spreadsheets/d/1_cI2TWjNddDOus2dvGEwRkRAADtAO70mfKFFKJH2gts).

Each row describes a perk; what it does is the Python function registered under
the same id in effects.py. The `perks` table is filled from this file at startup,
so changing a perk's name, rarity or durability is a CSV edit.

target_type says which glyphs a perk can go on: damage, heal_defense (heal or
defense glyphs) or any.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

CATALOG_FILE = Path(__file__).with_name("catalog.csv")
RARITIES = ("common", "uncommon", "rare", "legendary")
TARGETS = ("damage", "heal_defense", "any")
_ID = re.compile(r"[a-z0-9_]{1,32}")


@dataclass(frozen=True)
class PerkSpec:
    id: str
    name: str
    rarity: str
    description: str
    mechanics: str
    image: str | None
    durability: int | None  # None: never breaks
    quote: str | None
    target: str
    ready: bool  # only ready perks are offered in drafts


def _spec(line: int, row: dict[str, str]) -> PerkSpec:
    def fail(problem: str) -> ValueError:
        return ValueError(f"catalog.csv line {line}: {problem}")

    cell = {key: (value or "").strip() for key, value in row.items()}
    if not _ID.fullmatch(cell["id"]):
        raise fail(f"id {cell['id']!r} must be 1-32 of a-z, 0-9 and _")
    if not 1 <= len(cell["name"]) <= 20:
        raise fail("name must be 1-20 characters")
    if not 1 <= len(cell["description"]) <= 120:
        raise fail("description must be 1-120 characters")
    if len(cell["quote"]) > 120:
        raise fail("quote must be at most 120 characters")
    if cell["rarity"] not in RARITIES:
        raise fail(f"rarity must be one of {', '.join(RARITIES)}")
    if cell["target_type"] not in TARGETS:
        raise fail(f"target_type must be one of {', '.join(TARGETS)}")
    if cell["status"] not in ("ready", "not_ready"):
        raise fail("status must be ready or not_ready")
    durability = cell["durability"]
    if durability and not (durability.isdigit() and int(durability) > 0):
        raise fail("durability must be a positive whole number, or empty")
    return PerkSpec(
        id=cell["id"],
        name=cell["name"],
        rarity=cell["rarity"],
        description=cell["description"],
        mechanics=cell["mechanics"],
        image=cell["image"] or None,
        durability=int(durability) if durability else None,
        quote=cell["quote"] or None,
        target=cell["target_type"],
        ready=cell["status"] == "ready",
    )


def load_catalog(path: Path = CATALOG_FILE) -> dict[str, PerkSpec]:
    """Every row by id, in file order. Raises ValueError naming the bad row."""
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    catalog: dict[str, PerkSpec] = {}
    for line, row in enumerate(rows, start=2):
        spec = _spec(line, row)
        if spec.id in catalog:
            raise ValueError(f"catalog.csv line {line}: id {spec.id} appears twice")
        catalog[spec.id] = spec
    return catalog


CATALOG = load_catalog()
