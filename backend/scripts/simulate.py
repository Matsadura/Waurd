"""Bot-vs-bot matches on the real engine, to tune the letter table.

From the backend folder:

    uv run python scripts/simulate.py
    uv run python scripts/simulate.py --games 1000 --max-len 8
    uv run python scripts/simulate.py --scale 0.9 1 1 --shield 30

Each turn the bot casts the word worth the most (damage, healing, defense and
statuses), so it plays perfectly within its vocabulary. --max-len limits that
vocabulary: 5 is a casual player, 8 a strong one. The bots don't use the clock.

It prints the median match length, how often the first player wins, and how
many matches stall (no winner after 100 turns: healing and defense outpace
damage). Last run, with the table as it is: 15-18 turns, 53-55%, 0%.
"""

import argparse
import statistics
from collections import Counter
from pathlib import Path

import backend
from backend.game import setup
from backend.game.models import Glyph, Match, Player
from backend.game.rules import (
    STARTING_HP,
    VULNERABLE_PERCENT,
    WEAK_PERCENT,
    cast_word,
    pass_turn,
    select_perks,
    start_turn,
)

WORD_LIST = Path(backend.__file__).parent / "data" / "enable1.txt"
MAX_TURNS = 100


def mask_of(letters: str) -> int:
    mask = 0
    for c in letters:
        mask |= 1 << (ord(c) - ord("A"))
    return mask


def load_words(max_len: int) -> list[tuple[str, int, Counter]]:
    """Words the deck can spell, with a letter mask to skip most of them fast."""
    return [
        (word, mask_of(word), Counter(word))
        for word in setup.load_words(str(WORD_LIST))
        if 2 <= len(word) <= max_len and all(c in setup.LETTERS for c in word)
    ]


def worth(word: str, glyph_of: dict[str, Glyph], caster: Player, target: Player):
    """How good the word is now. Copies the engine's rules in game/rules.py."""
    totals = {"damage": 0, "heal": 0, "defense": 0}
    statuses: dict[str, int] = {}
    for c in word:
        g = glyph_of[c]
        if g.type == "skill":
            statuses[g.effect_type] = max(
                statuses.get(g.effect_type, 0), g.effect_value
            )
            continue
        value = g.effect_value
        if "weak" in caster.statuses:
            value = value * (100 - WEAK_PERCENT) // 100
        if g.effect_type == "damage" and "vulnerable" in target.statuses:
            value = value * (100 + VULNERABLE_PERCENT) // 100
        totals[g.effect_type] += value
    damage = min(target.hp, max(0, totals["damage"] - target.defense))
    if damage == target.hp:
        return 10_000.0  # a winning word beats everything
    healed = min(totals["heal"], STARTING_HP - caster.hp)
    # defense only helps if the opponent attacks; a new status is worth about
    # what it adds to or takes from one later cast
    score = damage + healed + 0.7 * totals["defense"]
    score += 6 * sum(target.statuses.get(e, 0) < t for e, t in statuses.items())
    return score


def take_turn(match: Match, words: list[tuple[str, int, Counter]]) -> None:
    me = match.active_player_index
    caster, target = match.players[me], match.players[1 - me]
    have = Counter(g.letter for g in caster.hand)
    hand_mask = mask_of("".join(have))
    glyph_of = {g.letter: g for g in caster.hand}  # copies of a letter are equal

    best, best_score = None, -1.0
    for word, mask, needed in words:
        if mask & ~hand_mask or any(have[c] < n for c, n in needed.items()):
            continue
        score = worth(word, glyph_of, caster, target)
        if score > best_score:
            best, best_score = word, score
    if best is None:
        pass_turn(match, me)
        return

    positions: list[int] = []
    for c in best:
        positions.append(
            next(
                i
                for i, g in enumerate(caster.hand)
                if g.letter == c and i not in positions
            )
        )
    cast_word(match, me, positions, {best})
    if match.winner is None:
        select_perks(match, me, [])  # the bots don't use perks yet: skip the draft


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", type=int, default=300)
    parser.add_argument("--max-len", type=int, default=6, help="longest word known")
    parser.add_argument(
        "--scale",
        nargs=3,
        type=float,
        default=(1.0, 1.0, 1.0),
        metavar=("DAMAGE", "HEAL", "DEFENSE"),
        help="multiply those glyph values",
    )
    parser.add_argument(
        "--shield", type=int, help="the second player's opening defense instead"
    )
    args = parser.parse_args()

    for letter, (kind, effect, value, copies) in list(setup.LETTERS.items()):
        k = {"damage": 0, "heal": 1, "defense": 2}.get(effect)
        if k is not None:
            scaled = max(1, round(value * args.scale[k]))
            setup.LETTERS[letter] = (kind, effect, scaled, copies)
    words = load_words(args.max_len)

    turns, first_wins, stalls = [], 0, 0
    for seed in range(args.games):
        match = setup.new_match(seed)
        first = match.active_player_index
        if args.shield is not None:
            match.players[1 - first].defense = args.shield
        start_turn(match)
        while match.winner is None and match.turn < MAX_TURNS:
            take_turn(match, words)
        turns.append(match.turn)
        first_wins += match.winner == first
        stalls += match.winner is None

    p10, *_, p90 = statistics.quantiles(turns, n=10)
    print(
        f"{args.games} matches, words up to {args.max_len} letters: "
        f"median {statistics.median(turns):g} turns (p10 {p10:.0f}, p90 {p90:.0f}), "
        f"first player wins {first_wins / args.games:.0%}, "
        f"stalls {stalls / args.games:.0%}"
    )


if __name__ == "__main__":
    main()
