"""One Python function per perk, registered under the perk's catalog id.

Two kinds of perk:

- A direct perk changes the glyph (or the deck) when it is applied:

      @perk("amplify", PerkKind.POWER_VALUE)
      def amplify(glyph: Glyph, ctx: PerkContext) -> bool: ...

  It returns True if it did something, False if it didn't apply (for
  example -ING- on a glyph that already reads ING); only True spends
  durability.

- A conditional perk fills the glyph's one bonus slot when applied, and its
  check runs when a word resolves:

      @conditional("last_plus_5")
      def last_plus_5(glyph: Glyph, ctx: WordContext, value: int) -> int: ...

apply.py handles the rules shared by every perk (target type, the bonus
slot, durability), so the functions only do their own part.
"""

import enum
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from backend.game.conditions import ConditionalRule
from backend.game.config import GameConfig
from backend.game.rng import Rng
from backend.game.state import Glyph, MatchState


class PerkKind(enum.StrEnum):
    """What a perk changes. Same names as the database's ModificationType."""

    EFFECT = "EFFECT"
    TYPE = "TYPE"
    POWER_VALUE = "POWER_VALUE"
    CONDITIONAL_SLOT = "CONDITIONAL_SLOT"
    LETTERS = "LETTERS"
    DECK = "DECK"


@dataclass(frozen=True, slots=True)
class PerkContext:
    """What a direct perk can use besides the glyph it's applied to."""

    state: MatchState
    player: int
    rng: Rng
    config: GameConfig


DirectPerk = Callable[[Glyph, PerkContext], bool]


@dataclass(frozen=True, slots=True)
class PerkDefinition:
    """A registered perk: exactly one of `apply` and `condition` is set."""

    id: str
    kind: PerkKind
    apply: DirectPerk | None = None
    condition: ConditionalRule | None = None

    @property
    def is_conditional(self) -> bool:
        return self.condition is not None


_REGISTRY: dict[str, PerkDefinition] = {}


def _register(definition: PerkDefinition) -> None:
    if definition.id in _REGISTRY:
        raise ValueError(f"Perk {definition.id} is registered twice.")
    _REGISTRY[definition.id] = definition


def perk(perk_id: str, kind: PerkKind) -> Callable[[DirectPerk], DirectPerk]:
    """Register a direct perk's function under its catalog id."""
    if kind == PerkKind.CONDITIONAL_SLOT:
        raise ValueError("Use @conditional for conditional perks.")

    def decorator(function: DirectPerk) -> DirectPerk:
        _register(PerkDefinition(perk_id, kind, apply=function))
        return function

    return decorator


def conditional(perk_id: str) -> Callable[[ConditionalRule], ConditionalRule]:
    """Register a conditional perk's resolution-time check under its id."""

    def decorator(function: ConditionalRule) -> ConditionalRule:
        _register(
            PerkDefinition(perk_id, PerkKind.CONDITIONAL_SLOT, condition=function)
        )
        return function

    return decorator


def registered() -> Mapping[str, PerkDefinition]:
    """Every registered perk by id."""
    return dict(_REGISTRY)


def conditional_rules() -> dict[str, ConditionalRule]:
    """The checks resolution runs for filled bonus slots, by perk id."""
    return {
        perk_id: definition.condition
        for perk_id, definition in _REGISTRY.items()
        if definition.condition is not None
    }
