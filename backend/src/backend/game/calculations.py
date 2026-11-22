K_FACTOR = 32
XP_PER_WIN = 50
XP_PER_LOSS = 20
LEVEL_STEP = 100


def xp_to_next(level: int) -> int:
    """XP needed to go from `level` to `level + 1`."""
    return LEVEL_STEP * level


def level_for(xp: int) -> int:
    """The level a player has reached with this much total XP."""
    level = 1
    while xp >= xp_to_next(level):
        xp -= xp_to_next(level)
        level += 1
    return level


def add_xp(user, amount: int) -> None:
    """Give XP and update the level to match. Use this for every XP source."""
    user.xp += amount
    user.level = level_for(user.xp)


def new_elo_ratings(winner: int, loser: int) -> tuple[int, int]:
    """Ratings after a win. Beating a stronger player moves both further."""
    expected = 1 / (1 + 10 ** ((loser - winner) / 400))
    change = round(K_FACTOR * (1 - expected))
    return winner + change, loser - change
