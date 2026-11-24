"""The achievements, and how far a player's stats take each one.

Progress is read from the totals in user_stats, so working it out again never
counts anything twice. The `achievements` table is filled from this list at
startup.
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
    progress: Callable[[UserStats], int]


ACHIEVEMENTS = [
    AchievementDef(
        "first-match",
        "First Steps",
        "Play your first match.",
        50,
        1,
        lambda stats: stats.matches_played,
    ),
    AchievementDef(
        "first-win",
        "First Win",
        "Win your first match.",
        100,
        1,
        lambda stats: stats.wins,
    ),
    AchievementDef(
        "ten-wins",
        "Seasoned",
        "Win 10 matches.",
        300,
        10,
        lambda stats: stats.wins,
    ),
    AchievementDef(
        "wordsmith",
        "Wordsmith",
        "Cast a word worth 100 or more.",
        250,
        100,
        lambda stats: stats.highest_word_score,
    ),
    AchievementDef(
        "heavy-hitter",
        "Heavy Hitter",
        "Deal 1,000 damage in total.",
        200,
        1000,
        lambda stats: stats.total_damage_dealt,
    ),
]
