import random

from backend.game.models import Glyph, Match, Player
from backend.game.rules import STARTING_HP

LETTERS = {
    "A": (6, 4),
    "E": (6, 4),
    "I": (6, 3),
    "O": (6, 3),
    "U": (6, 1),
    "N": (8, 2),
    "R": (8, 2),
    "S": (8, 3),
    "T": (8, 3),
    "L": (8, 2),
    "D": (10, 2),
    "C": (12, 1),
    "M": (12, 1),
    "P": (12, 1),
    "H": (12, 1),
    "G": (14, 1),
    "B": (20, 1),
    "F": (16, 1),
    "K": (18, 1),
    "W": (18, 1),
    "Y": (14, 1),
    "V": (20, 1),
}


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


def load_words(path: str) -> set[str]:
    with open(path) as file:
        return {line.strip().upper() for line in file if line.strip().isalpha()}
