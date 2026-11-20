"""Decks and piles: building a deck, starting a match, drawing, discarding."""

from backend.game.config import DEFAULT_CONFIG, GameConfig
from backend.game.rng import new_seed, rng_for
from backend.game.state import Glyph, MatchState, PlayerState


def build_deck(player: int, config: GameConfig = DEFAULT_CONFIG) -> list[Glyph]:
    """Build a player's unshuffled deck from the letter table.

    Glyph ids are "p{player}-g{n}", unique within the match.
    """
    deck: list[Glyph] = []
    for spec in config.letters:
        for _ in range(spec.copies):
            deck.append(
                Glyph(
                    id=f"p{player}-g{len(deck)}",
                    letters=spec.letter,
                    type=spec.type,
                    effect=spec.effect,
                    value=spec.value,
                )
            )
    return deck


def new_match(
    match_id: str,
    user_ids: tuple[str, str],
    time_control_seconds: int,
    seed: str | None = None,
    config: GameConfig = DEFAULT_CONFIG,
) -> MatchState:
    """Create a match in the WAITING phase with shuffled decks and empty hands.

    The seed decides both shuffles and who plays first; pass the same seed to
    get the same match.
    """
    if time_control_seconds not in config.time_controls:
        raise ValueError(f"{time_control_seconds}s is not an allowed time control.")
    if user_ids[0] == user_ids[1]:
        raise ValueError("A player can't play against themselves.")

    seed = new_seed() if seed is None else seed
    players = []
    for index, user_id in enumerate(user_ids):
        deck = build_deck(index, config)
        rng_for(seed, 0, "deck", player=index).shuffle(deck)
        players.append(
            PlayerState(
                user_id=user_id,
                hp=config.starting_hp,
                clock_ms=time_control_seconds * 1000,
                rerolls_left=config.rerolls_per_match,
                draw_pile=deck,
            )
        )

    first = rng_for(seed, 0, "first_player").randrange(2)
    players[1 - first].defense = config.second_player_shield
    return MatchState(
        match_id=match_id,
        seed=seed,
        time_control_seconds=time_control_seconds,
        players=players,
        active_player=first,
    )


def draw(state: MatchState, player: int, count: int) -> list[Glyph]:
    """Move up to `count` glyphs from the top of the draw pile to the hand.

    When the draw pile runs out, the discard pile is shuffled into a new draw
    pile and drawing continues. If both piles are empty, fewer glyphs are
    drawn. Returns the glyphs drawn, in order.
    """
    if count < 0:
        raise ValueError("Can't draw a negative number of glyphs.")
    side = state.player(player)
    drawn: list[Glyph] = []

    while len(drawn) < count:
        if not side.draw_pile:
            if not side.discard_pile:
                break
            _reshuffle(state, player)
        drawn.append(side.draw_pile.pop())

    side.hand.extend(drawn)
    return drawn


def _reshuffle(state: MatchState, player: int) -> None:
    side = state.player(player)
    side.draw_pile = side.discard_pile
    side.discard_pile = []
    purpose = f"reshuffle:{side.reshuffles}"
    rng_for(state.seed, state.turn, purpose, player=player).shuffle(side.draw_pile)
    side.reshuffles += 1


def discard_hand(state: MatchState, player: int) -> None:
    """Move the whole hand to the discard pile, as at the end of a turn."""
    side = state.player(player)
    side.discard_pile.extend(side.hand)
    side.hand = []
