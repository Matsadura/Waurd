"""The rules every perk shares: owning it, its target type, the bonus slot,
and durability.

PLACEHOLDER rules, to confirm with the team:
- Perks are applied to glyphs in the player's hand.
- A perk that doesn't apply (wrong glyph type, -ING- on an ING glyph, the
  same conditional again) changes nothing and spends no durability.
"""

import enum
from collections.abc import Mapping
from dataclasses import dataclass

from backend.game.config import DEFAULT_CONFIG, GameConfig
from backend.game.perks.catalog import PerkSpec, load_catalog
from backend.game.perks.registry import PerkContext, PerkDefinition, registered
from backend.game.rng import rng_for
from backend.game.state import Glyph, JSONDict, MatchState, PerkInstance


class PerkProblem(enum.StrEnum):
    UNKNOWN_INSTANCE = "UNKNOWN_INSTANCE"
    UNKNOWN_PERK = "UNKNOWN_PERK"
    GLYPH_NOT_IN_HAND = "GLYPH_NOT_IN_HAND"
    WRONG_TARGET = "WRONG_TARGET"


class PerkError(ValueError):
    """A perk move that can't be accepted; `problem` says why. The state is
    left unchanged."""

    def __init__(self, problem: PerkProblem, message: str) -> None:
        super().__init__(message)
        self.problem = problem


@dataclass(frozen=True, slots=True)
class PerkResult:
    """What applying a perk did. to_dict() is the PERK_APPLIED payload."""

    player: int
    instance_id: str
    perk_id: str
    glyph_id: str
    applied: bool
    durability_left: int | None
    destroyed: bool
    # The glyph afterwards; None when the perk removed it from the match.
    glyph: Glyph | None
    # The player's hand afterwards (some perks redraw glyphs).
    hand: tuple[Glyph, ...] = ()

    def to_dict(self) -> JSONDict:
        return {
            "player": self.player,
            "instance_id": self.instance_id,
            "perk_id": self.perk_id,
            "glyph_id": self.glyph_id,
            "applied": self.applied,
            "durability_left": self.durability_left,
            "destroyed": self.destroyed,
            "glyph": None if self.glyph is None else self.glyph.to_dict(),
            "hand": [glyph.to_dict() for glyph in self.hand],
        }


def check_catalog(
    catalog: Mapping[str, PerkSpec] | None = None,
    definitions: Mapping[str, PerkDefinition] | None = None,
) -> None:
    """Raise ValueError unless every catalog row has a registered function
    and every registered function has a row."""
    catalog = load_catalog() if catalog is None else catalog
    definitions = registered() if definitions is None else definitions
    missing = sorted(set(catalog) - set(definitions))
    if missing:
        raise ValueError(
            f"Perks in catalog.csv with no function: {', '.join(missing)}."
        )
    extra = sorted(set(definitions) - set(catalog))
    if extra:
        raise ValueError(f"Perk functions with no catalog.csv row: {', '.join(extra)}.")


def _lookup(
    perk_id: str,
    catalog: Mapping[str, PerkSpec],
    definitions: Mapping[str, PerkDefinition],
) -> tuple[PerkSpec, PerkDefinition]:
    if perk_id not in catalog or perk_id not in definitions:
        raise PerkError(PerkProblem.UNKNOWN_PERK, f"There is no perk {perk_id!r}.")
    return catalog[perk_id], definitions[perk_id]


def grant_perk(
    state: MatchState,
    player: int,
    perk_id: str,
    catalog: Mapping[str, PerkSpec] | None = None,
) -> PerkInstance:
    """Give a player a perk with its full catalog durability. Instance ids are
    "p{player}-k{n}", unique within the match."""
    catalog = load_catalog() if catalog is None else catalog
    spec, _ = _lookup(perk_id, catalog, registered())
    side = state.player(player)
    taken = {instance.instance_id for instance in side.perks}
    number = len(taken)
    while f"p{player}-k{number}" in taken:
        number += 1
    instance = PerkInstance(f"p{player}-k{number}", perk_id, spec.durability)
    side.perks.append(instance)
    return instance


def apply_perk(
    state: MatchState,
    player: int,
    instance_id: str,
    glyph_id: str,
    catalog: Mapping[str, PerkSpec] | None = None,
    config: GameConfig = DEFAULT_CONFIG,
) -> PerkResult:
    """Apply one of the player's perks to a glyph in their hand.

    Raises PerkError, changing nothing, when the player doesn't own the perk,
    the glyph isn't in their hand, or the perk doesn't target that glyph type.
    """
    catalog = load_catalog() if catalog is None else catalog
    side = state.player(player)
    instance = next((p for p in side.perks if p.instance_id == instance_id), None)
    if instance is None:
        raise PerkError(
            PerkProblem.UNKNOWN_INSTANCE, f"You don't have perk {instance_id!r}."
        )
    glyph = next((g for g in side.hand if g.id == glyph_id), None)
    if glyph is None:
        raise PerkError(
            PerkProblem.GLYPH_NOT_IN_HAND, f"Glyph {glyph_id!r} is not in your hand."
        )
    spec, definition = _lookup(instance.perk_id, catalog, registered())
    if not spec.supports(glyph.type):
        raise PerkError(
            PerkProblem.WRONG_TARGET,
            f"{spec.name} can't be used on a {glyph.type.value} glyph.",
        )

    if definition.condition is not None:
        # One bonus slot: a new conditional replaces the old one, the same one
        # again does nothing.
        applied = glyph.conditional_slot != instance.perk_id
        glyph.conditional_slot = instance.perk_id
    else:
        assert definition.apply is not None
        left = "unlimited" if instance.durability is None else instance.durability
        rng = rng_for(
            state.seed,
            state.turn,
            f"perk:{instance.instance_id}:{glyph.id}:{left}",
            player=player,
        )
        uses = 0
        if spec.durability is not None and instance.durability is not None:
            uses = spec.durability - instance.durability
        context = PerkContext(state, player, rng, config, uses)
        applied = definition.apply(glyph, context)

    destroyed = False
    if applied and instance.durability is not None:
        instance.durability -= 1
        if instance.durability == 0:
            side.perks = [p for p in side.perks if p.instance_id != instance_id]
            destroyed = True

    still_held = any(g.id == glyph.id for g in side.all_glyphs())
    return PerkResult(
        player=player,
        instance_id=instance_id,
        perk_id=instance.perk_id,
        glyph_id=glyph.id,
        applied=applied,
        durability_left=instance.durability,
        destroyed=destroyed,
        glyph=glyph if still_held else None,
        hand=tuple(side.hand),
    )
