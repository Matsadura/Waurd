"""What a conditional perk sees when a word resolves.

Shared by resolution (which runs the checks) and the perks (which define
them), so neither has to import the other.
"""

from collections.abc import Callable
from dataclasses import dataclass

from backend.game.state import Glyph

VOWELS = frozenset("AEIOU")


@dataclass(frozen=True, slots=True)
class WordContext:
    """Where a glyph sits in the cast word, for conditional perks."""

    word: str
    glyphs: tuple[Glyph, ...]
    index: int

    @property
    def is_first(self) -> bool:
        return self.index == 0

    @property
    def is_last(self) -> bool:
        return self.index == len(self.glyphs) - 1


# A conditional perk's check: gets the glyph, its place in the word and its
# value so far, returns the new value (the same value when the condition
# isn't met). Registered under the perk id stored in Glyph.conditional_slot.
ConditionalRule = Callable[[Glyph, WordContext, int], int]
