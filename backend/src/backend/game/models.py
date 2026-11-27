import random
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Glyph:
    letter: str
    effect_value: int
    # power: damage, heal or defense; skill: vulnerable or weak, and then
    # effect_value is how many of the target's turns the status lasts
    type: str = "power"
    effect_type: str = "damage"


@dataclass
class Player:
    hp: int
    draw_pile: list[Glyph] = field(default_factory=list)
    hand: list[Glyph] = field(default_factory=list)
    discard_pile: list[Glyph] = field(default_factory=list)
    time_left: float = 0.0
    defense: int = 0  # soaks up damage; gone when this player's next turn starts
    statuses: dict[str, int] = field(default_factory=dict)  # effect -> turns left


@dataclass
class Cast:
    turn: int
    player_index: int
    word: str
    glyphs: list[Glyph]
    damage: int  # the HP the opponent actually lost
    healed: int = 0  # the HP the caster actually got back
    defense: int = 0  # the defense the caster gained
    statuses: dict[str, int] = field(default_factory=dict)  # put on the target
    # naive UTC, like the database's DateTime columns
    cast_at: datetime = field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


@dataclass
class Match:
    players: list[Player]
    active_player_index: int = 0
    turn: int = 0
    winner: int | None = None
    rng: random.Random = field(default_factory=random.Random)
    end_reason: str | None = None
    clock_checked_at: float = 0.0
    casts: list[Cast] = field(default_factory=list)
    names: tuple[str, str] = ("Player 1", "Player 2")
    log: list[str] = field(default_factory=list)  # what happened, ready to show
