"""Match state: glyphs, players and the match, with JSON-safe serialization.

The runtime saves MatchState.to_dict() to Redis after every action and loads
it back with MatchState.from_dict(). The document carries a version so an old
saved state is rejected instead of being misread after the format changes.
"""

import enum
from dataclasses import dataclass, field
from typing import Any

from backend.game.config import Effect, GlyphType

# 2: PlayerState.draft_offer. 3: Status.applied_turn, PlayerState.ready.
STATE_VERSION = 3

JSONDict = dict[str, Any]


class Phase(enum.StrEnum):
    WAITING = "WAITING"
    ACTION = "ACTION"
    DRAFT = "DRAFT"
    ENDED = "ENDED"


class EndReason(enum.StrEnum):
    """Same names as the database's MatchEndReason."""

    HEALTH_DEPLETED = "HEALTH_DEPLETED"
    TIMEOUT = "TIMEOUT"
    RESIGNATION = "RESIGNATION"
    DISCONNECT = "DISCONNECT"


def _require(data: JSONDict, key: str) -> Any:
    try:
        return data[key]
    except KeyError:
        raise ValueError(f"Saved state is missing {key!r}.") from None


@dataclass(slots=True)
class Glyph:
    """A letter card. `letters` can hold several letters once a perk such as
    -ING- transforms it. `id` is unique within the match, e.g. "p0-g7"."""

    id: str
    letters: str
    type: GlyphType
    effect: Effect
    value: int
    # Id of the conditional perk filling the glyph's one bonus slot.
    conditional_slot: str | None = None

    def to_dict(self) -> JSONDict:
        return {
            "id": self.id,
            "letters": self.letters,
            "type": self.type.value,
            "effect": self.effect.value,
            "value": self.value,
            "conditional_slot": self.conditional_slot,
        }

    @classmethod
    def from_dict(cls, data: JSONDict) -> "Glyph":
        return cls(
            id=_require(data, "id"),
            letters=_require(data, "letters"),
            type=GlyphType(_require(data, "type")),
            effect=Effect(_require(data, "effect")),
            value=_require(data, "value"),
            conditional_slot=_require(data, "conditional_slot"),
        )


@dataclass(slots=True)
class Status:
    """A status effect (VULNERABLE or WEAK) and the turns it has left.

    `applied_turn` is the turn it was put on (or last extended); it doesn't
    count down at the end of that turn.
    """

    effect: Effect
    turns_left: int
    applied_turn: int = 0

    def to_dict(self) -> JSONDict:
        return {
            "effect": self.effect.value,
            "turns_left": self.turns_left,
            "applied_turn": self.applied_turn,
        }

    @classmethod
    def from_dict(cls, data: JSONDict) -> "Status":
        return cls(
            effect=Effect(_require(data, "effect")),
            turns_left=_require(data, "turns_left"),
            applied_turn=_require(data, "applied_turn"),
        )


@dataclass(slots=True)
class PerkInstance:
    """A perk a player owns. durability None means unlimited (achievement perks)."""

    instance_id: str
    perk_id: str
    durability: int | None

    def to_dict(self) -> JSONDict:
        return {
            "instance_id": self.instance_id,
            "perk_id": self.perk_id,
            "durability": self.durability,
        }

    @classmethod
    def from_dict(cls, data: JSONDict) -> "PerkInstance":
        return cls(
            instance_id=_require(data, "instance_id"),
            perk_id=_require(data, "perk_id"),
            durability=_require(data, "durability"),
        )


def _glyphs(data: JSONDict, key: str) -> list[Glyph]:
    return [Glyph.from_dict(item) for item in _require(data, key)]


@dataclass(slots=True)
class PlayerState:
    """One player's side of the match.

    The top of the draw pile is the end of the list.
    """

    user_id: str
    hp: int
    clock_ms: int
    rerolls_left: int
    defense: int = 0
    statuses: list[Status] = field(default_factory=list)
    draw_pile: list[Glyph] = field(default_factory=list)
    hand: list[Glyph] = field(default_factory=list)
    discard_pile: list[Glyph] = field(default_factory=list)
    perks: list[PerkInstance] = field(default_factory=list)
    # Sent PLAYER_READY; the match starts when both are ready.
    ready: bool = False
    # Perk ids offered in the current draft; empty when no draft is open.
    draft_offer: list[str] = field(default_factory=list)
    # How many times the discard pile was shuffled into the draw pile; gives
    # every reshuffle its own random generator.
    reshuffles: int = 0

    def all_glyphs(self) -> list[Glyph]:
        """Every glyph the player owns, wherever it is."""
        return [*self.draw_pile, *self.hand, *self.discard_pile]

    def to_dict(self) -> JSONDict:
        return {
            "user_id": self.user_id,
            "hp": self.hp,
            "defense": self.defense,
            "statuses": [status.to_dict() for status in self.statuses],
            "draw_pile": [glyph.to_dict() for glyph in self.draw_pile],
            "hand": [glyph.to_dict() for glyph in self.hand],
            "discard_pile": [glyph.to_dict() for glyph in self.discard_pile],
            "perks": [perk.to_dict() for perk in self.perks],
            "ready": self.ready,
            "draft_offer": list(self.draft_offer),
            "rerolls_left": self.rerolls_left,
            "clock_ms": self.clock_ms,
            "reshuffles": self.reshuffles,
        }

    @classmethod
    def from_dict(cls, data: JSONDict) -> "PlayerState":
        return cls(
            user_id=_require(data, "user_id"),
            hp=_require(data, "hp"),
            defense=_require(data, "defense"),
            statuses=[Status.from_dict(s) for s in _require(data, "statuses")],
            draw_pile=_glyphs(data, "draw_pile"),
            hand=_glyphs(data, "hand"),
            discard_pile=_glyphs(data, "discard_pile"),
            perks=[PerkInstance.from_dict(p) for p in _require(data, "perks")],
            ready=_require(data, "ready"),
            draft_offer=list(_require(data, "draft_offer")),
            rerolls_left=_require(data, "rerolls_left"),
            clock_ms=_require(data, "clock_ms"),
            reshuffles=_require(data, "reshuffles"),
        )


@dataclass(slots=True)
class MatchState:
    """The whole match. `turn` is 0 before the match starts, then 1, 2, 3...

    `active_player` and `winner` are indexes into `players`.
    """

    match_id: str
    seed: str
    time_control_seconds: int
    players: list[PlayerState]
    active_player: int
    turn: int = 0
    phase: Phase = Phase.WAITING
    winner: int | None = None
    end_reason: EndReason | None = None

    def __post_init__(self) -> None:
        if len(self.players) != 2:
            raise ValueError("A match has exactly two players.")
        if self.active_player not in (0, 1):
            raise ValueError("active_player must be 0 or 1.")

    def player(self, index: int) -> PlayerState:
        if index not in (0, 1):
            raise ValueError(f"Player index must be 0 or 1, not {index!r}.")
        return self.players[index]

    def to_dict(self) -> JSONDict:
        return {
            "version": STATE_VERSION,
            "match_id": self.match_id,
            "seed": self.seed,
            "time_control_seconds": self.time_control_seconds,
            "players": [player.to_dict() for player in self.players],
            "active_player": self.active_player,
            "turn": self.turn,
            "phase": self.phase.value,
            "winner": self.winner,
            "end_reason": self.end_reason.value if self.end_reason else None,
        }

    @classmethod
    def from_dict(cls, data: JSONDict) -> "MatchState":
        version = data.get("version")
        if version != STATE_VERSION:
            raise ValueError(
                f"Saved state has version {version!r}; this engine reads "
                f"version {STATE_VERSION}."
            )
        end_reason = _require(data, "end_reason")
        return cls(
            match_id=_require(data, "match_id"),
            seed=_require(data, "seed"),
            time_control_seconds=_require(data, "time_control_seconds"),
            players=[PlayerState.from_dict(p) for p in _require(data, "players")],
            active_player=_require(data, "active_player"),
            turn=_require(data, "turn"),
            phase=Phase(_require(data, "phase")),
            winner=_require(data, "winner"),
            end_reason=EndReason(end_reason) if end_reason is not None else None,
        )
