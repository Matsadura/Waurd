"""Every balance number the engine uses, in one validated, immutable object.

Values marked PLACEHOLDER answer open questions in the Game Design Document.
They are agreed defaults for now and still need confirming with the team.
"""

import enum
import string
from dataclasses import dataclass, field


class GlyphType(enum.StrEnum):
    POWER = "POWER"
    SKILL = "SKILL"


class Effect(enum.StrEnum):
    DAMAGE = "DAMAGE"
    DEFENSE = "DEFENSE"
    HEAL = "HEAL"
    VULNERABLE = "VULNERABLE"
    WEAK = "WEAK"


# For these effects a glyph's value is how many turns the status lasts.
STATUS_EFFECTS = frozenset({Effect.VULNERABLE, Effect.WEAK})


class Rarity(enum.StrEnum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    LEGENDARY = "LEGENDARY"


@dataclass(frozen=True, slots=True)
class LetterSpec:
    """One row of the letter table: what a letter's glyph does, and how many
    copies of it start in each deck."""

    letter: str
    type: GlyphType
    effect: Effect
    value: int
    copies: int


def _letter(
    letter: str, type_: GlyphType, effect: Effect, value: int, copies: int
) -> LetterSpec:
    return LetterSpec(letter, type_, effect, value, copies)


_P, _S = GlyphType.POWER, GlyphType.SKILL
_D, _DEF, _H = Effect.DAMAGE, Effect.DEFENSE, Effect.HEAL
_V, _W = Effect.VULNERABLE, Effect.WEAK

# PLACEHOLDER: the whole table. Values follow the GDD example (B 20 damage,
# R 15 defense, A 10 heal, V and E statuses for 2 turns). J, Q and X are not
# in the deck yet. The copies add up to a 40-glyph deck.
DEFAULT_LETTERS: tuple[LetterSpec, ...] = (
    _letter("A", _S, _H, 10, 3),
    _letter("E", _S, _W, 2, 4),
    _letter("I", _S, _H, 8, 3),
    _letter("O", _S, _DEF, 10, 3),
    _letter("U", _S, _H, 6, 1),
    _letter("N", _P, _D, 8, 2),
    _letter("R", _S, _DEF, 15, 2),
    _letter("S", _P, _D, 8, 3),
    _letter("T", _P, _D, 8, 3),
    _letter("L", _S, _DEF, 8, 2),
    _letter("D", _P, _D, 10, 2),
    _letter("C", _P, _D, 12, 1),
    _letter("M", _P, _D, 12, 1),
    _letter("P", _P, _D, 12, 1),
    _letter("H", _S, _DEF, 12, 1),
    _letter("G", _P, _D, 14, 1),
    _letter("B", _P, _D, 20, 1),
    _letter("F", _P, _D, 16, 1),
    _letter("K", _P, _D, 18, 1),
    _letter("W", _S, _DEF, 18, 1),
    _letter("Y", _S, _H, 14, 1),
    _letter("V", _S, _V, 2, 1),
    _letter("Z", _P, _D, 25, 1),
)

# PLACEHOLDER: the GDD's 60/28/15/3 adds up to 106%; these add up to 100.
DEFAULT_RARITY_WEIGHTS: tuple[tuple[Rarity, int], ...] = (
    (Rarity.COMMON, 60),
    (Rarity.UNCOMMON, 25),
    (Rarity.RARE, 12),
    (Rarity.LEGENDARY, 3),
)


@dataclass(frozen=True, slots=True)
class GameConfig:
    """Balance rules for one match. Invalid combinations raise ValueError."""

    # PLACEHOLDER: hand size, perk offers, picks and rerolls.
    hand_size: int = 7
    perks_per_turn: int = 3
    perks_to_select: int = 1
    rerolls_per_match: int = 3

    # PLACEHOLDER: HP. Healing can't go above max_hp.
    starting_hp: int = 100
    max_hp: int = 100

    # PLACEHOLDER: each player's clock is the match's time control, in seconds.
    time_controls: tuple[int, ...] = (60, 180, 300)

    # PLACEHOLDER: Vulnerable raises damage taken, Weak lowers Power glyph
    # values, both by this many percent.
    vulnerable_percent: int = 25
    weak_percent: int = 25

    # PLACEHOLDER: Defense resets at the start of its owner's next turn.
    defense_carries_over: bool = False

    rarity_weights: tuple[tuple[Rarity, int], ...] = DEFAULT_RARITY_WEIGHTS
    letters: tuple[LetterSpec, ...] = field(default=DEFAULT_LETTERS)

    # Not configurable, recorded here so they live next to the other rules:
    # PLACEHOLDER: glyph modifications from perks last for one match only.
    # PLACEHOLDER: a persistent achievement perk's durability resets every match.

    def __post_init__(self) -> None:
        self._validate_letters()
        self._validate_numbers()
        self._validate_rarities()

    @property
    def deck_size(self) -> int:
        return sum(spec.copies for spec in self.letters)

    def letter(self, letter: str) -> LetterSpec:
        """Return the table row for a letter, or raise KeyError."""
        for spec in self.letters:
            if spec.letter == letter:
                return spec
        raise KeyError(letter)

    def _validate_letters(self) -> None:
        if not self.letters:
            raise ValueError("The letter table is empty.")
        seen: set[str] = set()
        for spec in self.letters:
            if len(spec.letter) != 1 or spec.letter not in string.ascii_uppercase:
                raise ValueError(f"{spec.letter!r} is not a single letter A-Z.")
            if spec.letter in seen:
                raise ValueError(f"Letter {spec.letter} appears twice.")
            seen.add(spec.letter)
            if spec.copies < 1:
                raise ValueError(f"Letter {spec.letter} needs at least 1 copy.")
            minimum = 1 if spec.effect in STATUS_EFFECTS else 0
            if spec.value < minimum:
                raise ValueError(f"Letter {spec.letter} has value {spec.value}.")

    def _validate_numbers(self) -> None:
        if self.hand_size < 1:
            raise ValueError("hand_size must be at least 1.")
        if self.hand_size > self.deck_size:
            raise ValueError(
                f"hand_size {self.hand_size} is bigger than the "
                f"{self.deck_size}-glyph deck."
            )
        if self.perks_per_turn < 1:
            raise ValueError("perks_per_turn must be at least 1.")
        if not 1 <= self.perks_to_select <= self.perks_per_turn:
            raise ValueError("perks_to_select must be between 1 and perks_per_turn.")
        if self.rerolls_per_match < 0:
            raise ValueError("rerolls_per_match can't be negative.")
        if not 0 < self.starting_hp <= self.max_hp:
            raise ValueError("starting_hp must be between 1 and max_hp.")
        if not self.time_controls or any(t <= 0 for t in self.time_controls):
            raise ValueError("time_controls must be positive numbers of seconds.")
        if len(set(self.time_controls)) != len(self.time_controls):
            raise ValueError("time_controls has a duplicate.")
        for name in ("vulnerable_percent", "weak_percent"):
            if not 0 <= getattr(self, name) <= 100:
                raise ValueError(f"{name} must be between 0 and 100.")

    def _validate_rarities(self) -> None:
        rarities = [rarity for rarity, _ in self.rarity_weights]
        if len(set(rarities)) != len(rarities):
            raise ValueError("rarity_weights has a duplicate rarity.")
        if any(weight < 0 for _, weight in self.rarity_weights):
            raise ValueError("rarity_weights can't be negative.")
        total = sum(weight for _, weight in self.rarity_weights)
        if total != 100:
            raise ValueError(f"rarity_weights add up to {total}, not 100.")


DEFAULT_CONFIG = GameConfig()
