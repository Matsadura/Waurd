from dataclasses import dataclass, field


@dataclass
class Glyph:
    letter: str
    damage: int


@dataclass
class Player:
    hp: int
    draw_pile: list[Glyph] = field(default_factory=list)
    hand: list[Glyph] = field(default_factory=list)
    discard_pile: list[Glyph] = field(default_factory=list)


@dataclass
class Match:
    players: list[Player]
    active_player_index: int = 0
    turn: int = 0
    winner: int | None = None
