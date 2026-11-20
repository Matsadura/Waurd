"""The perks in catalog.csv. Each function is registered under its row's id.

Adding a perk: add its row to catalog.csv and its function here. The test
suite fails if a row has no function or a function has no row.

A direct perk returns True when it changed something and False when it
didn't apply (only True spends durability). Weak and Vulnerable glyphs hold a
duration, not an amount, so value perks leave them alone; only Linger
lengthens them.
"""

from itertools import pairwise

from backend.game.conditions import VOWELS, WordContext
from backend.game.config import STATUS_EFFECTS, Effect, GlyphType
from backend.game.perks.registry import PerkContext, PerkKind, conditional, perk
from backend.game.piles import discard_hand, draw
from backend.game.state import Glyph

COMMON_CONSONANTS = ("S", "T", "N", "R", "L", "D")


def _is_status(glyph: Glyph) -> bool:
    return glyph.effect in STATUS_EFFECTS


# Value ----------------------------------------------------------------------


@perk("sharpen", PerkKind.POWER_VALUE)
def sharpen(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value += 4
    return True


@perk("fortify", PerkKind.POWER_VALUE)
def fortify(glyph: Glyph, ctx: PerkContext) -> bool:
    if _is_status(glyph):
        return False
    glyph.value += 6
    return True


@perk("round_up", PerkKind.POWER_VALUE)
def round_up(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value = (glyph.value // 5 + 1) * 5
    return True


@perk("double_or_halve", PerkKind.POWER_VALUE)
def double_or_halve(glyph: Glyph, ctx: PerkContext) -> bool:
    # Halving rounds down.
    glyph.value = glyph.value * 2 if ctx.rng.random() < 0.6 else glyph.value // 2
    return True


@perk("snowball", PerkKind.POWER_VALUE)
def snowball(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value += 3 * (ctx.uses + 1)
    return True


@perk("blood", PerkKind.POWER_VALUE)
def blood(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value += 15
    side = ctx.state.player(ctx.player)
    side.hp = max(1, side.hp - 8)
    return True


@perk("amplify", PerkKind.POWER_VALUE)
def amplify(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value = glyph.value * 3 // 2
    return True


@perk("overcharge", PerkKind.POWER_VALUE)
def overcharge(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value = glyph.value * 5 // 2
    return True


# Letters --------------------------------------------------------------------


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


@perk("ed", PerkKind.LETTERS)
def ed(glyph: Glyph, ctx: PerkContext) -> bool:
    return _transform(glyph, "ED", 5)


@perk("pluralize", PerkKind.LETTERS)
def pluralize(glyph: Glyph, ctx: PerkContext) -> bool:
    return _transform(glyph, "S", 3)


@perk("qu", PerkKind.LETTERS)
def qu(glyph: Glyph, ctx: PerkContext) -> bool:
    return _transform(glyph, "QU", 18)


def _shift(glyph: Glyph, ctx: PerkContext, letters: tuple[str, ...]) -> bool:
    choices = [letter for letter in letters if letter != glyph.letters]
    glyph.letters = ctx.rng.choice(choices)
    return True


@perk("vowel_shift", PerkKind.LETTERS)
def vowel_shift(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value += 2
    return _shift(glyph, ctx, tuple(sorted(VOWELS)))


@perk("consonant_shift", PerkKind.LETTERS)
def consonant_shift(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.value += 4
    return _shift(glyph, ctx, COMMON_CONSONANTS)


# Type and effect ------------------------------------------------------------


@perk("wild_power", PerkKind.TYPE)
def wild_power(glyph: Glyph, ctx: PerkContext) -> bool:
    if _is_status(glyph):
        return False
    glyph.type = GlyphType.POWER
    glyph.effect = Effect.DAMAGE
    glyph.value += 4
    return True


@perk("wild_skill", PerkKind.TYPE)
def wild_skill(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.type = GlyphType.SKILL
    glyph.effect = ctx.rng.choice((Effect.DEFENSE, Effect.HEAL))
    glyph.value += 6
    return True


def _curse(ctx: PerkContext, effect: Effect, turns: int) -> bool:
    ctx.state.player(1 - ctx.player).add_status(effect, turns, ctx.state.turn)
    return True


# Applied straight to the opponent during your turn. A status counts every
# turn of the match from the next one, so 3 turns of Weak cover the
# opponent's next two casts, and Vulnerable (already on for this cast)
# covers this cast and your next.
@perk("hex", PerkKind.EFFECT)
def hex_(glyph: Glyph, ctx: PerkContext) -> bool:
    return _curse(ctx, Effect.WEAK, 3)


@perk("expose", PerkKind.EFFECT)
def expose(glyph: Glyph, ctx: PerkContext) -> bool:
    return _curse(ctx, Effect.VULNERABLE, 3)


@perk("linger", PerkKind.EFFECT)
def linger(glyph: Glyph, ctx: PerkContext) -> bool:
    opponent = ctx.state.player(1 - ctx.player)
    if not opponent.statuses:
        return _curse(ctx, Effect.WEAK, 2)
    for status in opponent.statuses:
        status.turns_left += 2
    return True


# Deck -----------------------------------------------------------------------


def _boost(glyphs: list[Glyph], amount: int) -> None:
    for glyph in glyphs:
        if not _is_status(glyph):
            glyph.value += amount


@perk("erase", PerkKind.DECK)
def erase(glyph: Glyph, ctx: PerkContext) -> bool:
    # Perks apply to glyphs in hand; leaving the hand here means leaving the
    # match, since it never reaches the discard pile.
    side = ctx.state.player(ctx.player)
    side.hand = [g for g in side.hand if g.id != glyph.id]
    draw(ctx.state, ctx.player, 1)
    return True


@perk("redraw", PerkKind.DECK)
def redraw(glyph: Glyph, ctx: PerkContext) -> bool:
    side = ctx.state.player(ctx.player)
    side.hand = [g for g in side.hand if g.id != glyph.id]
    side.discard_pile.append(glyph)
    _boost(draw(ctx.state, ctx.player, 1), 5)
    return True


@perk("fresh_start", PerkKind.DECK)
def fresh_start(glyph: Glyph, ctx: PerkContext) -> bool:
    discard_hand(ctx.state, ctx.player)
    _boost(draw(ctx.state, ctx.player, ctx.config.hand_size), 3)
    return True


# Conditional perks: the check runs when the word resolves -------------------


@conditional("last_bonus")
def last_bonus(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 9 if ctx.is_last else value


@conditional("first_bonus")
def first_bonus(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 9 if ctx.is_first else value


@conditional("last_double")
def last_double(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 2 if ctx.is_last else value


@conditional("first_double")
def first_double(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 2 if ctx.is_first else value


@conditional("vowel_start")
def vowel_start(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 12 if ctx.word[:1] in VOWELS else value


@conditional("five_letters")
def five_letters(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 8 if len(ctx.word) == 5 else value


@conditional("matching_ends")
def matching_ends(glyph: Glyph, ctx: WordContext, value: int) -> int:
    word = ctx.word
    return value * 3 if len(word) >= 2 and word[0] == word[-1] else value


@conditional("quick_jab")
def quick_jab(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 14 if len(ctx.word) <= 3 else value


@conditional("twin_letters")
def twin_letters(glyph: Glyph, ctx: WordContext, value: int) -> int:
    word = ctx.word
    doubled = any(a == b for a, b in pairwise(word))
    return value + 14 if doubled else value


@conditional("late_bloomer")
def late_bloomer(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 3 // 2 if ctx.position >= 3 else value


@conditional("long_word")
def long_word(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 2 if len(ctx.word) >= 6 else value


@conditional("onslaught")
def onslaught(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 3 * sum(g.type == GlyphType.POWER for g in ctx.glyphs)


@conditional("lexicon")
def lexicon(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 2 * max(0, len(ctx.word) - 2)


@conditional("climber")
def climber(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 3 * min(ctx.position - 1, 5)


@conditional("desperation")
def desperation(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 2 if ctx.caster_hp * 10 <= ctx.max_hp * 3 else value


@conditional("executioner")
def executioner(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 3 if ctx.target_hp * 10 <= ctx.max_hp * 4 else value


@conditional("grand_finale")
def grand_finale(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value * 3 if ctx.is_last and len(ctx.word) >= 5 else value
