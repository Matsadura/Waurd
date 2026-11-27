"""Populate the database with deterministic data for local development.

Achievements come from game/achievements.py, the same as in real matches:
the definitions are synced, then each seed player's progress is worked out
from their stats (and their XP raised by what they completed).
"""

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from backend.core.security import hash_password
from backend.db.session import async_session_maker
from backend.game.achievements import ACHIEVEMENTS
from backend.game.calculations import add_xp
from backend.models import Achievement, User, UserStats
from backend.ws.records import record_achievements, sync_achievements

SEED_USER_IDS = tuple(
    uuid.UUID(f"00000000-0000-4000-8000-00000000000{n}").bytes for n in range(1, 5)
)
SEED_PASSWORD = "SecureP@ssw0rd!123"


def build_seed_data() -> list[tuple[User, int, UserStats]]:
    """Each seed user with the XP they start with (before achievements) and stats."""

    def player(n, username, email, xp, elo, password=True, **stats):  # type: ignore[no-untyped-def]
        user_id = SEED_USER_IDS[n]
        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=hash_password(SEED_PASSWORD) if password else None,
            xp=0,
            level=1,
            is_online=False,
        )
        if not password:  # a Google-only account
            user.oauth_provider = "GOOGLE"
            user.oauth_id = f"mock-google-{username}"
        return user, xp, UserStats(user_id=user_id, rating_elo=elo, **stats)

    return [
        player(
            0,
            "alice_wizard",
            "alice@email.com",
            2450,
            1420,
            matches_played=42,
            wins=31,
            losses=8,
            draws=3,
            highest_scoring_word="QUIZZIFY",
            highest_word_score=184,
            total_damage_dealt=12840,
        ),
        player(
            1,
            "bob_builder",
            "bob@email.com",
            980,
            1185,
            matches_played=18,
            wins=9,
            losses=7,
            draws=2,
            highest_scoring_word="JAZZ",
            highest_word_score=96,
            total_damage_dealt=5320,
        ),
        player(
            2,
            "casey_caster",
            "casey@email.com",
            5200,
            1675,
            password=False,
            matches_played=67,
            wins=54,
            losses=10,
            draws=3,
            highest_scoring_word="OXYPHENBUTAZONE",
            highest_word_score=312,
            total_damage_dealt=24110,
        ),
        player(
            3,
            "stats_user",
            "stats@email.com",
            1350,
            1260,
            matches_played=25,
            wins=14,
            losses=9,
            draws=2,
            highest_scoring_word="JUMP",
            highest_word_score=118,
            total_damage_dealt=7640,
        ),
    ]


async def seed_database(reset: bool = False) -> None:
    seed = build_seed_data()
    await sync_achievements()  # also done at startup; needed before the rows below

    async with async_session_maker() as session:
        exists = await session.get(User, SEED_USER_IDS[0])
        if exists is not None and not reset:
            print(
                "The seed users already exist; run again with --reset to replace them."
            )
            return
        if reset:
            # stats and achievement progress go with the users (ON DELETE CASCADE)
            await session.execute(delete(User).where(User.id.in_(SEED_USER_IDS)))
            # achievements no longer in game/achievements.py, e.g. the old
            # "streak-master" from earlier seeds
            defined = [achievement.id for achievement in ACHIEVEMENTS]
            await session.execute(
                delete(Achievement).where(Achievement.id.not_in(defined))
            )
            await session.commit()

        for user, xp, stats in seed:
            add_xp(user, xp)
            session.add(user)
            session.add(stats)
        await session.flush()
        for user_id in SEED_USER_IDS:
            await record_achievements(session, user_id)
        await session.commit()

        seeded = (
            await session.scalars(
                select(User)
                .where(User.id.in_(SEED_USER_IDS))
                .options(selectinload(User.stats), selectinload(User.achievements))
            )
        ).all()
        if len(seeded) != len(seed) or any(user.stats is None for user in seeded):
            raise RuntimeError("Seed verification failed: users or stats missing")

        completed = sum(
            row.is_completed for user in seeded for row in user.achievements
        )
        print(
            f"Seeded {len(seeded)} users with stats; {completed} achievements "
            f"completed from their stats."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete the seed users (and achievements no longer defined) first",
    )
    args = parser.parse_args()
    asyncio.run(seed_database(reset=args.reset))


if __name__ == "__main__":
    main()
