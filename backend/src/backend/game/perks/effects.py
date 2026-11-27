"""One function per perk in catalog.csv, registered under the row's id.

Two kinds:

- A direct perk changes the glyph (or the deck, or the opponent) when it is
  applied. It returns True when it did something; only then is durability spent.

      @perk("amplify", "POWER_VALUE")
      def amplify(glyph, ctx): ...

- A bonus perk fills the glyph's bonus slot when applied; its check runs when the
  word is cast and returns the glyph's new value.

      @bonus("last_bonus")
      def last_bonus(glyph, word, value): ...

play.py holds the rules every perk shares (targets, durability, the slot).
Weak and vulnerable glyphs hold a number of turns, not an amount, so value
changes and bonus slots leave them alone.
"""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise

from backend.game.deck import draw
from backend.game.models import Glyph, Match, Player

VOWELS = "AEIOU"
COMMON_CONSONANTS = "STNRLD"


@dataclass(frozen=True)
class PerkContext:
    """What a direct perk can use besides its glyph."""

    match: Match
    player: int
    uses: int  # times this perk instance was used before

    @property
    def me(self) -> Player:
        return self.match.players[self.player]

    @property
    def opponent(self) -> Player:
        return self.match.players[1 - self.player]


@dataclass(frozen=True)
class WordContext:
    """Where a glyph sits in the word being cast, for bonus perks."""

    word: str
    glyphs: list[Glyph]
    index: int
    caster_hp: int  # before the word resolves
    target_hp: int
    max_hp: int

    @property
    def position(self) -> int:  # 1 for the first glyph
        return self.index + 1

    @property
    def is_first(self) -> bool:
        return self.index == 0

    @property
    def is_last(self) -> bool:
        return self.index == len(self.glyphs) - 1


DirectPerk = Callable[[Glyph, PerkContext], bool]
BonusPerk = Callable[[Glyph, WordContext, int], int]
DIRECT: dict[str, DirectPerk] = {}
BONUS: dict[str, BonusPerk] = {}
# what each perk changes, the perks table's modification_type: POWER_VALUE,
# LETTERS, TYPE, EFFECT, DECK or CONDITIONAL_SLOT (every bonus perk)
KIND: dict[str, str] = {}


def perk(perk_id: str, kind: str) -> Callable[[DirectPerk], DirectPerk]:
    def register(fn: DirectPerk) -> DirectPerk:
        DIRECT[perk_id] = fn
        KIND[perk_id] = kind
        return fn

    return register


def bonus(perk_id: str) -> Callable[[BonusPerk], BonusPerk]:
    def register(fn: BonusPerk) -> BonusPerk:
        BONUS[perk_id] = fn
        KIND[perk_id] = "CONDITIONAL_SLOT"
        return fn

    return register


def is_status(glyph: Glyph) -> bool:
    return glyph.type == "skill"


def _raise_value(glyph: Glyph, amount: int) -> None:
    if not is_status(glyph):
        glyph.effect_value += amount


# Value ------------------------------------------------------------------------


@perk("sharpen", "POWER_VALUE")
def sharpen(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_value += 4
    return True


@perk("fortify", "POWER_VALUE")
def fortify(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_value += 6
    return True


@perk("round_up", "POWER_VALUE")
def round_up(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_value = (glyph.effect_value // 5 + 1) * 5
    return True


@perk("double_or_halve", "POWER_VALUE")
def double_or_halve(glyph: Glyph, ctx: PerkContext) -> bool:
    if ctx.match.rng.random() < 0.6:
        glyph.effect_value *= 2
    else:
        glyph.effect_value //= 2
    return True


@perk("snowball", "POWER_VALUE")
def snowball(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_value += 3 * (ctx.uses + 1)
    return True


@perk("blood", "POWER_VALUE")
def blood(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_value += 15
    ctx.me.hp = max(1, ctx.me.hp - 8)
    return True


@perk("amplify", "POWER_VALUE")
def amplify(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_value = glyph.effect_value * 3 // 2
    return True


@perk("overcharge", "POWER_VALUE")
def overcharge(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_value = glyph.effect_value * 5 // 2
    return True


# Letters ----------------------------------------------------------------------


def _become(glyph: Glyph, letters: str, amount: int) -> bool:
    if glyph.letter == letters:
        return False
    glyph.letter = letters
    glyph.effect_value += amount
    return True


@perk("ing", "LETTERS")
def ing(glyph: Glyph, ctx: PerkContext) -> bool:
    return _become(glyph, "ING", 7)


@perk("er", "LETTERS")
def er(glyph: Glyph, ctx: PerkContext) -> bool:
    return _become(glyph, "ER", 5)


@perk("re", "LETTERS")
def re_(glyph: Glyph, ctx: PerkContext) -> bool:
    return _become(glyph, "RE", 5)


@perk("ed", "LETTERS")
def ed(glyph: Glyph, ctx: PerkContext) -> bool:
    return _become(glyph, "ED", 5)


@perk("pluralize", "LETTERS")
def pluralize(glyph: Glyph, ctx: PerkContext) -> bool:
    return _become(glyph, "S", 3)


@perk("qu", "LETTERS")
def qu(glyph: Glyph, ctx: PerkContext) -> bool:
    return _become(glyph, "QU", 18)


def _shift(glyph: Glyph, ctx: PerkContext, letters: str, amount: int) -> bool:
    glyph.letter = ctx.match.rng.choice([c for c in letters if c != glyph.letter])
    _raise_value(glyph, amount)
    return True


@perk("vowel_shift", "LETTERS")
def vowel_shift(glyph: Glyph, ctx: PerkContext) -> bool:
    return _shift(glyph, ctx, VOWELS, 2)


@perk("consonant_shift", "LETTERS")
def consonant_shift(glyph: Glyph, ctx: PerkContext) -> bool:
    return _shift(glyph, ctx, COMMON_CONSONANTS, 4)


# Effect -----------------------------------------------------------------------


@perk("wild_power", "TYPE")
def wild_power(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_type = "damage"
    glyph.effect_value += 4
    return True


@perk("wild_skill", "TYPE")
def wild_skill(glyph: Glyph, ctx: PerkContext) -> bool:
    glyph.effect_type = ctx.match.rng.choice(("defense", "heal"))
    glyph.effect_value += 6
    return True


def _curse(ctx: PerkContext, effect: str, turns: int) -> bool:
    statuses = ctx.opponent.statuses
    statuses[effect] = max(statuses.get(effect, 0), turns)
    return True


# Put straight on the opponent. A status counts down at the end of its owner's
# turns, so Vulnerable is already on for this turn's word.
@perk("hex", "EFFECT")
def hex_(glyph: Glyph, ctx: PerkContext) -> bool:
    return _curse(ctx, "weak", 3)


@perk("expose", "EFFECT")
def expose(glyph: Glyph, ctx: PerkContext) -> bool:
    return _curse(ctx, "vulnerable", 3)


@perk("linger", "EFFECT")
def linger(glyph: Glyph, ctx: PerkContext) -> bool:
    statuses = ctx.opponent.statuses
    if not statuses:
        return _curse(ctx, "weak", 2)
    for effect in statuses:
        statuses[effect] += 2
    return True


# Deck -------------------------------------------------------------------------


@perk("erase", "DECK")
def erase(glyph: Glyph, ctx: PerkContext) -> bool:
    ctx.me.hand.remove(glyph)  # never reaches a pile: it leaves the match
    draw(ctx.match, ctx.me, 1)
    return True


@perk("redraw", "DECK")
def redraw(glyph: Glyph, ctx: PerkContext) -> bool:
    ctx.me.hand.remove(glyph)
    ctx.me.discard_pile.append(glyph)
    for drawn in draw(ctx.match, ctx.me, 1):
        _raise_value(drawn, 5)
    return True


@perk("fresh_start", "DECK")
def fresh_start(glyph: Glyph, ctx: PerkContext) -> bool:
    count = len(ctx.me.hand)
    ctx.me.discard_pile += ctx.me.hand
    ctx.me.hand = []
    for drawn in draw(ctx.match, ctx.me, count):
        _raise_value(drawn, 3)
    return True


# Bonus slots: checked when the word is cast -----------------------------------


@bonus("last_bonus")
def last_bonus(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 9 if word.is_last else value


@bonus("first_bonus")
def first_bonus(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 9 if word.is_first else value


@bonus("last_double")
def last_double(glyph: Glyph, word: WordContext, value: int) -> int:
    return value * 2 if word.is_last else value


@bonus("first_double")
def first_double(glyph: Glyph, word: WordContext, value: int) -> int:
    return value * 2 if word.is_first else value


@bonus("vowel_start")
def vowel_start(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 12 if word.word[:1] in VOWELS else value


@bonus("five_letters")
def five_letters(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 8 if len(word.word) == 5 else value


@bonus("matching_ends")
def matching_ends(glyph: Glyph, word: WordContext, value: int) -> int:
    w = word.word
    return value * 3 if len(w) >= 2 and w[0] == w[-1] else value


@bonus("quick_jab")
def quick_jab(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 14 if len(word.word) <= 3 else value


@bonus("twin_letters")
def twin_letters(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 14 if any(a == b for a, b in pairwise(word.word)) else value


@bonus("late_bloomer")
def late_bloomer(glyph: Glyph, word: WordContext, value: int) -> int:
    return value * 3 // 2 if word.position >= 3 else value


@bonus("long_word")
def long_word(glyph: Glyph, word: WordContext, value: int) -> int:
    return value * 2 if len(word.word) >= 6 else value


@bonus("onslaught")
def onslaught(glyph: Glyph, word: WordContext, value: int) -> int:
    # "Power glyphs" in the sheet's sense: the ones that deal damage
    return value + 3 * sum(g.effect_type == "damage" for g in word.glyphs)


@bonus("lexicon")
def lexicon(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 2 * max(0, len(word.word) - 2)


@bonus("climber")
def climber(glyph: Glyph, word: WordContext, value: int) -> int:
    return value + 3 * min(word.position - 1, 5)


@bonus("desperation")
def desperation(glyph: Glyph, word: WordContext, value: int) -> int:
    return value * 2 if word.caster_hp * 10 <= word.max_hp * 3 else value


@bonus("executioner")
def executioner(glyph: Glyph, word: WordContext, value: int) -> int:
    return value * 3 if word.target_hp * 10 <= word.max_hp * 4 else value


@bonus("grand_finale")
def grand_finale(glyph: Glyph, word: WordContext, value: int) -> int:
    return value * 3 if word.is_last and len(word.word) >= 5 else value
