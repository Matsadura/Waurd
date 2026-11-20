"""The perks in catalog.csv. Each function is registered under its row's id.

Adding a perk: add its row to catalog.csv and its function here. The test
suite fails if a row has no function or a function has no row.
"""

from backend.game.conditions import VOWELS, WordContext
from backend.game.perks.registry import PerkContext, PerkKind, conditional, perk
from backend.game.state import Glyph

# Direct perks ---------------------------------------------------------------


@perk("double_or_halve", PerkKind.POWER_VALUE)
def double_or_halve(glyph: Glyph, ctx: PerkContext) -> bool:
    # Halving rounds down.
    glyph.value = glyph.value * 2 if ctx.rng.random() < 0.5 else glyph.value // 2
    return True


def _transform(glyph: Glyph, letters: str, bonus: int) -> bool:
    if glyph.letters == letters:
        return False
    glyph.letters = letters
    glyph.value += bonus
    return True


@perk("ing", PerkKind.LETTERS)
def ing(glyph: Glyph, ctx: PerkContext) -> bool:
    return _transform(glyph, "ING", 7)


@perk("er", PerkKind.LETTERS)
def er(glyph: Glyph, ctx: PerkContext) -> bool:
    return _transform(glyph, "ER", 5)


@perk("re", PerkKind.LETTERS)
def re_(glyph: Glyph, ctx: PerkContext) -> bool:
    return _transform(glyph, "RE", 5)


@perk("erase", PerkKind.DECK)
def erase(glyph: Glyph, ctx: PerkContext) -> bool:
    # Perks apply to glyphs in hand; leaving the hand here means leaving the
    # match, since it never reaches the discard pile.
    side = ctx.state.player(ctx.player)
    side.hand = [g for g in side.hand if g.id != glyph.id]
    return True


@perk("amplify", PerkKind.POWER_VALUE)
def amplify(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value *= 2
    return True


# Conditional perks: the check runs when the word resolves -------------------


@conditional("last_plus_5")
def last_plus_5(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 5 if ctx.is_last else value


@conditional("first_plus_5")
def first_plus_5(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 5 if ctx.is_first else value


@conditional("last_times_2")
def last_times_2(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 2 if ctx.is_last else value


@conditional("first_times_2")
def first_times_2(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 2 if ctx.is_first else value


@conditional("vowel_start_plus_10")
def vowel_start_plus_10(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 10 if ctx.word[:1] in VOWELS else value


@conditional("five_letters_plus_8")
def five_letters_plus_8(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 8 if len(ctx.word) == 5 else value


@conditional("matching_ends_x2")
def matching_ends_x2(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 2 if ctx.word[:1] == ctx.word[-1:] else value
