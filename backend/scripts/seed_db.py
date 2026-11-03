"""Populate the database with deterministic data for local development."""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from backend.core.security import hash_password
from backend.db.session import async_session_maker
from backend.models import Achievement, User, UserAchievement, UserStats

SEED_USER_IDS = (
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000002",
    "00000000-0000-4000-8000-000000000003",
    "00000000-0000-4000-8000-000000000004",
)
SEED_ACHIEVEMENT_IDS = ("first-win", "wordsmith", "streak-master")
SEED_PASSWORD = "SecureP@ssw0rd!123"


def build_seed_data() -> tuple[
    list[User], list[Achievement], list[UserStats], list[UserAchievement]
]:
    users = [
        User(
            id=SEED_USER_IDS[0],
            username="alice_wizard",
            email="alice@email.com",
            password_hash=hash_password(SEED_PASSWORD),
            xp=2450,
            elo=1420,
            level=12,
            is_online=True,
        ),
        User(
            id=SEED_USER_IDS[1],
            username="bob_builder",
            email="bob@email.com",
            password_hash=hash_password(SEED_PASSWORD),
            xp=980,
            elo=1185,
            level=7,
            is_online=False,
        ),
        User(
            id=SEED_USER_IDS[2],
            username="casey_caster",
            email="casey@email.com",
            password_hash=None,
            oauth_provider="GOOGLE",
            oauth_id="mock-google-casey",
            xp=5200,
            elo=1675,
            level=24,
            is_online=False,
        ),
        User(
            id=SEED_USER_IDS[3],
            username="stats_user",
            email="stats@email.com",
            password_hash=hash_password(SEED_PASSWORD),
            xp=1350,
            elo=1260,
            level=9,
            is_online=False,
        ),
    ]
    achievements = [
        Achievement(
            id="first-win",
            name="First Win",
            description="Win your first match.",
            icon_url="https://example.test/icons/first-win.png",
            xp_reward=100,
        ),
        Achievement(
            id="wordsmith",
            name="Wordsmith",
            description="Score at least 100 points with one word.",
            icon_url="https://example.test/icons/wordsmith.png",
            xp_reward=250,
        ),
        Achievement(
            id="streak-master",
            name="Streak Master",
            description="Win five matches in a row.",
            icon_url="https://example.test/icons/streak-master.png",
            xp_reward=500,
        ),
    ]
    stats = [
        UserStats(
            user_id=SEED_USER_IDS[0],
            matches_played=42,
            wins=31,
            losses=8,
            draws=3,
            rating_elo=1420,
            highest_scoring_word="QUIZZIFY",
            highest_word_score=184,
            total_damage_dealt=12840,
        ),
        UserStats(
            user_id=SEED_USER_IDS[1],
            matches_played=18,
            wins=9,
            losses=7,
            draws=2,
            rating_elo=1185,
            highest_scoring_word="JAZZ",
            highest_word_score=96,
            total_damage_dealt=5320,
        ),
        UserStats(
            user_id=SEED_USER_IDS[2],
            matches_played=67,
            wins=54,
            losses=10,
            draws=3,
            rating_elo=1675,
            highest_scoring_word="OXYPHENBUTAZONE",
            highest_word_score=312,
            total_damage_dealt=24110,
        ),
        UserStats(
            user_id=SEED_USER_IDS[3],
            matches_played=25,
            wins=14,
            losses=9,
            draws=2,
            rating_elo=1260,
            highest_scoring_word="JUMP",
            highest_word_score=118,
            total_damage_dealt=7640,
        ),
    ]
    user_achievements = [
        UserAchievement(user_id=SEED_USER_IDS[0], achievement_id="first-win"),
        UserAchievement(user_id=SEED_USER_IDS[0], achievement_id="wordsmith"),
        UserAchievement(user_id=SEED_USER_IDS[1], achievement_id="first-win"),
        UserAchievement(user_id=SEED_USER_IDS[2], achievement_id="first-win"),
        UserAchievement(user_id=SEED_USER_IDS[2], achievement_id="wordsmith"),
        UserAchievement(user_id=SEED_USER_IDS[2], achievement_id="streak-master"),
        UserAchievement(user_id=SEED_USER_IDS[3], achievement_id="first-win"),
    ]
    return users, achievements, stats, user_achievements


async def seed_database(reset: bool = False) -> None:
    users, achievements, stats, user_achievements = build_seed_data()

    async with async_session_maker() as session:
        if reset:
            await session.execute(
                delete(UserAchievement).where(
                    UserAchievement.user_id.in_(SEED_USER_IDS)
                )
            )
            await session.execute(
                delete(UserStats).where(UserStats.user_id.in_(SEED_USER_IDS))
            )
            await session.execute(delete(User).where(User.id.in_(SEED_USER_IDS)))
            await session.execute(
                delete(Achievement).where(Achievement.id.in_(SEED_ACHIEVEMENT_IDS))
            )

        for achievement in achievements:
            await session.merge(achievement)
        for user in users:
            await session.merge(user)
        for stat in stats:
            await session.merge(stat)
        for user_achievement in user_achievements:
            await session.merge(user_achievement)
        await session.commit()

        result = await session.execute(
            select(User)
            .where(User.id.in_(SEED_USER_IDS))
            .options(
                selectinload(User.stats),
                selectinload(User.achievements).selectinload(
                    UserAchievement.achievement
                ),
            )
        )
        seeded_users = result.scalars().all()

        if len(seeded_users) != len(users) or any(
            user.stats is None or not user.achievements for user in seeded_users
        ):
            raise RuntimeError(
                "Seed verification failed: relationships were not loaded"
            )

        print(
            f"Seeded {len(seeded_users)} users, {len(achievements)} achievements, "
            f"and {len(user_achievements)} user achievements."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete the fixed seed records before inserting them",
    )
    args = parser.parse_args()
    asyncio.run(seed_database(reset=args.reset))


if __name__ == "__main__":
    main()
