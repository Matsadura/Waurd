from backend.game.models import Match

HAND_SIZE = 12
STARTING_HP = 100
TURN_SECONDS = 30


def start_turn(match: Match) -> None:
    """Start a new turn: the active player draws up to HAND_SIZE glyphs."""
    match.turn += 1
    match.turn_tume_used = 0.0
    player = match.players[match.active_player_index]
    while len(player.hand) < HAND_SIZE:
        if not player.draw_pile:
            if not player.discard_pile:
                break
            player.draw_pile = player.discard_pile
            player.discard_pile = []
            match.rng.shuffle(player.draw_pile)
        player.hand.append(player.draw_pile.pop())


def cast_word(
    match: Match, player_index: int, positions: list[int], words: set[str]
) -> None:
    """Cast a word for the given player."""
    if match.winner is not None:
        raise ValueError("Match is already over.")
    if player_index != match.active_player_index:
        raise ValueError("It's not your turn.")

    caster = match.players[player_index]
    if any(type(i) is not int for i in positions):
        raise ValueError("Positions must be whole numbers.")
    if not positions:
        raise ValueError("Pick at least one glyph.")
    if len(set(positions)) != len(positions):
        raise ValueError("A glyph can only be used once.")
    if any(not 0 <= i < len(caster.hand) for i in positions):
        raise ValueError("The glyph position is out of bounds.")

    glyphs_to_cast = [caster.hand[i] for i in positions]
    word = "".join(glyph.letter for glyph in glyphs_to_cast)
    if word not in words:
        raise ValueError(f"{word} is an invalid word.")

    target = match.players[1 - player_index]
    target.hp = max(0, target.hp - sum(glyph.damage for glyph in glyphs_to_cast))

    caster.discard_pile += caster.hand
    caster.hand = []

    if target.hp == 0:
        match.winner = player_index
        match.end_reason = "HEALTH_DEPLETED"
        return
    match.active_player_index = 1 - player_index
    start_turn(match)


def pass_turn(match: Match, player_index: int) -> None:
    """Pass the turn for the given player."""
    if match.winner is not None:
        raise ValueError("Match is already over.")
    if player_index != match.active_player_index:
        raise ValueError("It's not your turn.")

    player = match.players[player_index]
    player.discard_pile += player.hand
    player.hand = []

    match.active_player_index = 1 - player_index
    start_turn(match)


def resign(match: Match, player_index: int) -> None:
    """Resign the match for the given player."""
    if match.winner is not None:
        raise ValueError("Match is already over.")
    match.winner = 1 - player_index
    match.end_reason = "RESIGNATION"


def lose_by_disconnect(match: Match, player_index: int) -> None:
    """The player left and didn't come back in time: the other player wins."""
    if match.winner is not None:
        raise ValueError("Match is already over.")
    match.winner = 1 - player_index
    match.end_reason = "DISCONNECT"


def use_time(match: Match, now: float) -> None:
    """Charge the active player for the time since the last check.

    `now` is any steadily increasing clock in seconds (the runtime passes
    time.monotonic()). Running out of match time loses the match; using up
    the turn's TURN_SECONDS passes the turn.
    """
    elapsed = now - match.clock_checked_at
    match.clock_checked_at = now
    if match.winner is not None or match.turn == 0:
        return

    elapsed = min(elapsed, TURN_SECONDS - match.turn_time_used)
    player = match.players[match.active_player_index]
    player.time_left = max(0.0, player.time_left - elapsed)
    match.turn_time_used += elapsed

    if player.time_left == 0:
        match.winner = 1 - match.active_player_index
        match.end_reason = "TIMEOUT"
        return
    if match.turn_time_used >= TURN_SECONDS:
        pass_turn(match, match.active_player_index)
