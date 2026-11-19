"""Spelling a word from hand positions and checking that it's a real word.

The engine never loads a word list itself: the caller passes something that
answers "is this a word?" (the Dictionary protocol). Words are uppercase
throughout, matching glyph letters.
"""

import enum
from collections.abc import Collection, Sequence
from typing import Protocol

from backend.game.state import Glyph


class Dictionary(Protocol):
    """Anything that can say whether an uppercase word is valid."""

    def __contains__(self, word: object) -> bool: ...


class SpellingProblem(enum.StrEnum):
    NO_GLYPHS = "NO_GLYPHS"
    POSITION_OUT_OF_RANGE = "POSITION_OUT_OF_RANGE"
    REPEATED_POSITION = "REPEATED_POSITION"
    UNKNOWN_WORD = "UNKNOWN_WORD"


class SpellingError(ValueError):
    """A cast that can't be accepted; `problem` says why."""

    def __init__(self, problem: SpellingProblem, message: str) -> None:
        super().__init__(message)
        self.problem = problem


def selected_glyphs(hand: Sequence[Glyph], positions: Sequence[int]) -> list[Glyph]:
    """Return the hand glyphs at `positions`, in that order.

    Positions are 0-based indexes into the hand. Each may be used once, and
    negative numbers are out of range rather than counting from the end.
    """
    if not positions:
        raise SpellingError(SpellingProblem.NO_GLYPHS, "Choose at least one glyph.")

    seen: set[int] = set()
    glyphs: list[Glyph] = []
    for position in positions:
        if (
            not isinstance(position, int)
            or isinstance(position, bool)
            or not 0 <= position < len(hand)
        ):
            raise SpellingError(
                SpellingProblem.POSITION_OUT_OF_RANGE,
                f"Position {position!r} is not in the hand.",
            )
        if position in seen:
            raise SpellingError(
                SpellingProblem.REPEATED_POSITION,
                f"Position {position} is used twice.",
            )
        seen.add(position)
        glyphs.append(hand[position])
    return glyphs


def spell(hand: Sequence[Glyph], positions: Sequence[int]) -> str:
    """Build the word the positions spell. Multi-letter glyphs add all their letters."""
    return "".join(glyph.letters for glyph in selected_glyphs(hand, positions))


def check_word(
    word: str,
    dictionary: Dictionary,
    achievement_words: Collection[str] = (),
) -> None:
    """Raise SpellingError unless `word` is in the dictionary or is one of the
    achievement-list words (which count even if the dictionary lacks them)."""
    word = word.upper()
    if word in dictionary:
        return
    if word in {extra.upper() for extra in achievement_words}:
        return
    raise SpellingError(SpellingProblem.UNKNOWN_WORD, f"{word} is not a valid word.")


def validate_cast(
    hand: Sequence[Glyph],
    positions: Sequence[int],
    dictionary: Dictionary,
    achievement_words: Collection[str] = (),
) -> str:
    """Spell the word and check it; returns the word or raises SpellingError."""
    word = spell(hand, positions)
    check_word(word, dictionary, achievement_words)
    return word
