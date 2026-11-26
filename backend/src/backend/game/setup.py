import random

from backend.game.models import Glyph, Match, Player
from backend.game.rules import STARTING_HP

# letter: (type, effect, value, copies). Effects follow the demo/full-game table;
# a skill glyph's value is how many of the target's turns its status lasts.
LETTERS = {
    "A": ("power", "heal", 9, 4),
    "E": ("skill", "weak", 2, 4),
    "I": ("power", "heal", 7, 3),
    "O": ("power", "defense", 9, 3),
    "U": ("power", "heal", 5, 1),
    "N": ("power", "damage", 8, 2),
    "R": ("power", "defense", 14, 2),
    "S": ("power", "damage", 8, 3),
    "T": ("power", "damage", 8, 3),
    "L": ("power", "defense", 7, 2),
    "D": ("power", "damage", 10, 2),
    "C": ("power", "damage", 12, 1),
    "M": ("power", "damage", 12, 1),
    "P": ("power", "damage", 12, 1),
    "H": ("power", "defense", 11, 1),
    "G": ("power", "damage", 14, 1),
    "B": ("power", "damage", 20, 1),
    "F": ("power", "damage", 16, 1),
    "K": ("power", "damage", 18, 1),
    "W": ("power", "defense", 16, 1),
    "Y": ("power", "heal", 13, 1),
    "V": ("skill", "vulnerable", 2, 1),
}


def build_deck() -> list[Glyph]:
    deck = []
    for letter, (kind, effect, value, copies) in LETTERS.items():
        deck += [Glyph(letter, value, kind, effect) for _ in range(copies)]
    return deck


def new_match(seed: int | None, time_control_seconds: int = 300) -> Match:
    """Each player's clock starts with the whole time control."""
    rng = random.Random(seed)
    players = []
    for _ in range(2):
        deck = build_deck()
        rng.shuffle(deck)
        players.append(
            Player(hp=STARTING_HP, draw_pile=deck, time_left=time_control_seconds)
        )
    return Match(players=players, rng=rng, active_player_index=rng.randrange(2))


def load_words(path: str) -> set[str]:
    with open(path) as file:
        return {line.strip().upper() for line in file if line.strip().isalpha()}
