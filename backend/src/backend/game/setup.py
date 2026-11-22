import random

from backend.game.models import Glyph, Match, Player
from backend.game.rules import LETTERS, STARTING_HP


def build_deck() -> list[Glyph]:
    deck = []
    for letter, (damage, copies) in LETTERS.items():
        deck += [Glyph(letter, damage) for _ in range(copies)]
    return deck


def new_match(seed: int | None) -> Match:
    rng = random.Random(seed)
    players = []
    for _ in range(2):
        deck = build_deck()
        rng.shuffle(deck)
        players.append(Player(hp=STARTING_HP, draw_pile=deck))
    return Match(players=players, rng=rng)
