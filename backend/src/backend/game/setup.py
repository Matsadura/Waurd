import random

from backend.game.balance import (
    DEFAULT_TIME_CONTROL,
    LETTERS,
    REROLLS_PER_MATCH,
    SECOND_PLAYER_SHIELD,
    STARTING_HP,
)
from backend.game.models import Glyph, Match, Player
from backend.game.perks import play as perks


def build_deck() -> list[Glyph]:
    deck = []
    for letter, (kind, effect, value, copies) in LETTERS.items():
        deck += [Glyph(letter, value, kind, effect) for _ in range(copies)]
    return deck


def new_match(
    seed: int | None,
    time_control_seconds: int = DEFAULT_TIME_CONTROL,
    loadouts: tuple[list[str], list[str]] = ([], []),
) -> Match:
    """Each player's clock starts with the whole time control, and their
    equipped loadout perks start in hand."""
    rng = random.Random(seed)
    players = []
    for _ in range(2):
        deck = build_deck()
        rng.shuffle(deck)
        players.append(
            Player(hp=STARTING_HP, draw_pile=deck, time_left=time_control_seconds)
        )
    first = rng.randrange(2)
    players[1 - first].defense = SECOND_PLAYER_SHIELD
    match = Match(players=players, rng=rng, active_player_index=first)
    for seat, perk_ids in enumerate(loadouts):
        match.players[seat].rerolls_left = REROLLS_PER_MATCH
        for perk_id in perk_ids:
            perks.grant(match, seat, perk_id)
    return match


def load_words(path: str) -> set[str]:
    with open(path) as file:
        return {line.strip().upper() for line in file if line.strip().isalpha()}
