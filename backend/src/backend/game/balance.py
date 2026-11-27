"""Every number that balances the game, in one place.

Change a value here, then check it with the simulation from the backend folder:

    uv run python scripts/simulate.py --games 1000

Not here: each perk's own numbers live in the perk sheet / game/perks/catalog.csv
(rarity, durability) and in its function in game/perks/effects.py (+4, x2...);
achievement targets and rewards are in game/achievements.py.
"""

# Match ------------------------------------------------------------------------

STARTING_HP = 100  # also the most HP healing can reach
HAND_SIZE = 12  # glyphs drawn up to at the start of each turn
# Defense the second player starts with, soaking up the opening word (gone when
# their first turn starts). Simulated: without it the first player wins about
# 82% of matches; with 35 about 53-55%, matches lasting a median 15-18 turns.
SECOND_PLAYER_SHIELD = 35

# Clocks: each player's clock starts with the whole time control, in seconds.
TIME_CONTROLS = [180, 300, 600]
DEFAULT_TIME_CONTROL = 300  # for private lobbies created without one
# How long a disconnected player has to come back before they lose (and how
# long the second player has to arrive before the match is aborted).
GRACE_SECONDS = 30

# Statuses ---------------------------------------------------------------------

VULNERABLE_PERCENT = 50  # extra damage a vulnerable player takes
WEAK_PERCENT = 25  # how much a weak player's power glyphs lose

# Letters ----------------------------------------------------------------------

# letter: (type, effect, value, copies in each deck). A skill glyph's value is
# how many of the target's turns its status lasts. 40 glyphs per deck.
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

# Perks ------------------------------------------------------------------------

DRAFT_SIZE = 3  # perks offered after each cast
REROLLS_PER_MATCH = 3
# How often each rarity is offered in a draft, relative to the others.
RARITY_WEIGHTS = {"common": 60, "uncommon": 25, "rare": 12, "legendary": 3}
MAX_LOADOUT_SLOTS = 3  # perks a player can equip; they start every match in hand

# Rating and progression -------------------------------------------------------

STARTING_ELO = 1200
ELO_K_FACTOR = 32  # how far one result moves both ratings
MAX_ALLOWED_ELO_DIFF = 200  # quick matches only pair players this close
XP_PER_WIN = 50
XP_PER_LOSS = 20
# XP to go from level n to n + 1 is LEVEL_STEP * n: 100, 200, 300...
LEVEL_STEP = 100
