from dataclasses import replace

from backend.game.models import Cast, Glyph, Match

HAND_SIZE = 12
STARTING_HP = 100  # also the most HP healing can reach
VULNERABLE_PERCENT = 50  # extra damage a vulnerable player takes
WEAK_PERCENT = 25  # how much a weak player's power glyphs lose
# Defense the second player starts with, soaking up the opening word (gone when
# their first turn starts). Simulated: without it the first player wins about
# 82% of matches; with 35 about 53-55%, matches lasting a median 15-18 turns.
SECOND_PLAYER_SHIELD = 35


def start_turn(match: Match) -> None:
    """Start a new turn: the active player draws up to HAND_SIZE glyphs."""
    match.turn += 1
    if match.turn == 1:
        match.log.append(f"{match.names[match.active_player_index]} goes first")
    player = match.players[match.active_player_index]
    player.defense = 0
    while len(player.hand) < HAND_SIZE:
        if not player.draw_pile:
            if not player.discard_pile:
                break
            player.draw_pile = player.discard_pile
            player.discard_pile = []
            match.rng.shuffle(player.draw_pile)
        player.hand.append(player.draw_pile.pop())


def attack_of(glyphs: list[Glyph]) -> int:
    """A word's raw damage: its damage glyphs before statuses, defense and HP."""
    return sum(g.effect_value for g in glyphs if g.effect_type == "damage")


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
    totals = {"damage": 0, "heal": 0, "defense": 0}
    statuses: dict[str, int] = {}
    for glyph in glyphs_to_cast:
        if glyph.type == "skill":
            turns = statuses.get(glyph.effect_type, 0)
            statuses[glyph.effect_type] = max(turns, glyph.effect_value)
            continue
        value = glyph.effect_value
        # percentages round down glyph by glyph: weak first, then vulnerable
        if "weak" in caster.statuses:
            value = value * (100 - WEAK_PERCENT) // 100
        if glyph.effect_type == "damage" and "vulnerable" in target.statuses:
            value = value * (100 + VULNERABLE_PERCENT) // 100
        totals[glyph.effect_type] += value

    blocked = min(totals["damage"], target.defense)
    target.defense -= blocked
    damage = min(target.hp, totals["damage"] - blocked)
    target.hp -= damage
    healed = min(totals["heal"], STARTING_HP - caster.hp)
    caster.hp += healed
    caster.defense += totals["defense"]
    # statuses start after the word; a status already there keeps the longer time
    for effect, turns in statuses.items():
        target.statuses[effect] = max(target.statuses.get(effect, 0), turns)

    match.casts.append(
        Cast(
            turn=match.turn,
            player_index=player_index,
            word=word,
            glyphs=[
                replace(glyph) for glyph in glyphs_to_cast
            ],  # copies: perks may change the originals later
            damage=damage,
        )
    )
    line = f"{match.names[player_index]} cast {word} for {damage} damage"
    if blocked:
        line += f" ({blocked} blocked)"
    if healed:
        line += f", healed {healed}"
    if totals["defense"]:
        line += f", +{totals['defense']} defense"
    for effect, turns in statuses.items():
        s = "" if turns == 1 else "s"
        line += f", {match.names[1 - player_index]} is {effect} for {turns} turn{s}"
    match.log.append(line)

    if target.hp == 0:
        caster.discard_pile += caster.hand
        caster.hand = []
        match.winner = player_index
        match.end_reason = "HEALTH_DEPLETED"
        win(match, f"{match.names[1 - player_index]} has no HP left")
        return
    end_turn(match, player_index)


def end_turn(match: Match, player_index: int) -> None:
    """Discard the hand, count down the player's statuses, start the other turn."""
    player = match.players[player_index]
    player.discard_pile += player.hand
    player.hand = []
    player.statuses = {e: t - 1 for e, t in player.statuses.items() if t > 1}
    match.active_player_index = 1 - player_index
    start_turn(match)


def pass_turn(match: Match, player_index: int) -> None:
    """Pass the turn for the given player."""
    if match.winner is not None:
        raise ValueError("Match is already over.")
    if player_index != match.active_player_index:
        raise ValueError("It's not your turn.")

    match.log.append(f"{match.names[player_index]} passed")
    end_turn(match, player_index)


def resign(match: Match, player_index: int) -> None:
    """Resign the match for the given player."""
    if match.winner is not None:
        raise ValueError("Match is already over.")
    match.winner = 1 - player_index
    match.end_reason = "RESIGNATION"
    win(match, f"{match.names[player_index]} resigned")


def lose_by_disconnect(match: Match, player_index: int) -> None:
    """The player left and didn't come back in time: the other player wins."""
    if match.winner is not None:
        raise ValueError("Match is already over.")
    match.winner = 1 - player_index
    match.end_reason = "DISCONNECT"
    win(match, f"{match.names[player_index]} didn't come back in time")


def use_time(match: Match, now: float) -> None:
    """Charge the active player for the time since the last check.

    `now` is any steadily increasing clock in seconds (the runtime passes
    time.monotonic()). Running out of time loses the match.
    """
    elapsed = now - match.clock_checked_at
    match.clock_checked_at = now
    if match.winner is not None or match.turn == 0:
        return

    player = match.players[match.active_player_index]
    player.time_left = max(0.0, player.time_left - elapsed)
    if player.time_left == 0:
        match.winner = 1 - match.active_player_index
        match.end_reason = "TIMEOUT"
        win(match, f"{match.names[match.active_player_index]} ran out of time")


def win(match: Match, why: str) -> None:
    """The log's last line: why the match ended and who won."""
    match.log.append(f"{why}. {match.names[match.winner]} wins!")
