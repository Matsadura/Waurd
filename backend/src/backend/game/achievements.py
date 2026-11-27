"""The achievements, and how far a player has got with each one.

Progress is read from totals: the player's user_stats, and the different words
they have ever cast (from match_casts). Working it out again never counts
anything twice. The `achievements` table is filled from this list at startup.
"""

from collections.abc import Callable
from dataclasses import dataclass

from backend.models.user_stats import UserStats


@dataclass(frozen=True)
class AchievementDef:
    id: str
    name: str
    description: str
    xp_reward: int
    target_value: int
    progress: Callable[[UserStats, set[str]], int]  # stats, words ever cast
    # unlocked with the achievement for the loadout; must be a row in `perks`
    reward_perk_id: str | None = None


# Word collections: every word is in the word list and can be spelled from a
# deck (no J, Q, X or Z). Any `target_value` of them completes the collection.
ANIMALS = frozenset(
    "CAT DOG WOLF BEAR LION TIGER HORSE MOUSE SNAKE EAGLE HAWK OWL RAT BAT COW PIG"
    " HEN DEER DUCK GOAT SHEEP CAMEL SEAL CRAB FROG TOAD MOLE ELK EMU YAK APE ANT"
    " BEE EEL OTTER RAVEN SHARK WHALE".split()
)
PLANTS = frozenset(
    "TREE ROSE FERN MOSS OAK PINE ELM VINE LILY IRIS TULIP DAISY PALM REED WEED"
    " SEED LEAF BUD ROOT CEDAR MAPLE LOTUS ASPEN".split()
)
ELEMENTS = frozenset(
    "FIRE WATER EARTH WIND STORM FLAME STONE RAIN SNOW ICE LAVA MIST CLOUD THUNDER"
    " FROST STEAM SPARK EMBER TIDE".split()
)

ACHIEVEMENTS = [
    AchievementDef(
        "first-match",
        "First Steps",
        "Play your first match.",
        50,
        1,
        lambda stats, words: stats.matches_played,
    ),
    AchievementDef(
        "first-win",
        "First Win",
        "Win your first match.",
        100,
        1,
        lambda stats, words: stats.wins,
    ),
    AchievementDef(
        "ten-wins",
        "Seasoned",
        "Win 10 matches.",
        300,
        10,
        lambda stats, words: stats.wins,
    ),
    AchievementDef(
        "wordsmith",
        "Wordsmith",
        "Cast a word worth 100 or more.",
        250,
        100,
        lambda stats, words: stats.highest_word_score,
    ),
    AchievementDef(
        "heavy-hitter",
        "Heavy Hitter",
        "Deal 1,000 damage in total.",
        200,
        1000,
        lambda stats, words: stats.total_damage_dealt,
    ),
    AchievementDef(
        "wild-wolf",
        "Wild Wolf",
        "Cast 5 different animal names.",
        150,
        5,
        lambda stats, words: len(words & ANIMALS),
    ),
    AchievementDef(
        "green-thumb",
        "Green Thumb",
        "Cast 5 different plant names.",
        150,
        5,
        lambda stats, words: len(words & PLANTS),
    ),
    AchievementDef(
        "elementalist",
        "Elementalist",
        "Cast 5 different elements of nature, like FIRE or STORM.",
        150,
        5,
        lambda stats, words: len(words & ELEMENTS),
    ),
]
