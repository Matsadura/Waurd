"""Public player profiles: GET /players/{id} and /players/{id}/matches."""

import uuid
from datetime import datetime

import pytest

from backend.models import (
    Achievement,
    FriendshipStatus,
    Match,
    MatchStatus,
    User,
    UserAchievement,
    UserStats,
)

PRIVATE = {
    "email",
    "role",
    "oauth_provider",
    "two_factor_enabled",
    "password_hash",
    "xp",
}


def uid(user) -> str:  # type: ignore[no-untyped-def]
    return str(uuid.UUID(bytes=user.id))


async def give(session_maker, *rows) -> None:  # type: ignore[no-untyped-def]
    async with session_maker() as db:
        for row in rows:
            db.add(row)
        await db.commit()


async def add_match(session_maker, p1, p2, status, number):  # type: ignore[no-untyped-def]
    await give(
        session_maker,
        Match(
            id=uuid.UUID(int=number).bytes,
            player1_id=p1.id,
            player2_id=p2.id,
            time_control_seconds=300,
            status=status,
            winner_id=p1.id if status == MatchStatus.FINISHED else None,
        ),
    )


class TestPlayerProfile:
    async def test_shows_safe_fields_only(self, alice_client, bob) -> None:
        response = await alice_client.get(f"/players/{uid(bob)}")

        assert response.status_code == 200
        body = response.json()
        assert (body["id"], body["username"]) == (uid(bob), "bob")
        assert not PRIVATE & set(body)
        assert set(body) == {
            "id",
            "username",
            "avatar_url",
            "created_at",
            "level",
            "xp_into_level",
            "xp_for_next_level",
            "is_online",
            "last_seen_at",
            "stats",
            "achievements",
        }

    async def test_shows_level_progress_from_xp(
        self, alice_client, bob, session_maker
    ) -> None:
        async with session_maker() as db:
            row = await db.get(User, bob.id)
            row.xp, row.level = 250, 2  # 100 to reach level 2, then 150 of 200
            await db.commit()

        body = (await alice_client.get(f"/players/{uid(bob)}")).json()

        assert (body["level"], body["xp_into_level"], body["xp_for_next_level"]) == (
            2,
            150,
            200,
        )

    async def test_shows_stats(self, alice_client, bob, session_maker) -> None:
        await give(
            session_maker,
            UserStats(
                user_id=bob.id,
                rating_elo=1350,
                wins=7,
                losses=2,
                best_win_streak=4,
                highest_scoring_word="QUIZ",
                highest_word_score=40,
            ),
        )

        stats = (await alice_client.get(f"/players/{uid(bob)}")).json()["stats"]

        assert (stats["rating_elo"], stats["wins"], stats["best_win_streak"]) == (
            1350,
            7,
            4,
        )
        assert stats["highest_scoring_word"] == "QUIZ"

    async def test_stats_are_null_when_there_are_none(self, alice_client, bob) -> None:
        assert (await alice_client.get(f"/players/{uid(bob)}")).json()["stats"] is None

    async def test_lists_only_completed_achievements_newest_first(
        self, alice_client, bob, session_maker
    ) -> None:
        await give(
            session_maker,
            *[
                Achievement(
                    id=a, name=a.title(), description="d", icon_url="", xp_reward=50
                )
                for a in ("first-win", "ten-wins", "wordsmith")
            ],
        )
        await give(
            session_maker,
            UserAchievement(
                user_id=bob.id,
                achievement_id="first-win",
                current_progress=1,
                is_completed=True,
                unlocked_at=datetime(2026, 1, 1),
            ),
            UserAchievement(
                user_id=bob.id,
                achievement_id="wordsmith",
                current_progress=1,
                is_completed=True,
                unlocked_at=datetime(2026, 2, 1),
            ),
            UserAchievement(
                user_id=bob.id,
                achievement_id="ten-wins",
                current_progress=3,
                is_completed=False,
                unlocked_at=datetime(2026, 1, 15),
            ),
        )

        achievements = (await alice_client.get(f"/players/{uid(bob)}")).json()[
            "achievements"
        ]

        assert [a["achievement_id"] for a in achievements] == ["wordsmith", "first-win"]
        assert achievements[0]["name"] == "Wordsmith"

    async def test_strangers_do_not_see_online_status(
        self, alice_client, carol, session_maker
    ) -> None:
        async with session_maker() as db:
            (await db.get(User, carol.id)).is_online = True
            await db.commit()

        stranger = (await alice_client.get(f"/players/{uid(carol)}")).json()

        assert (stranger["is_online"], stranger["last_seen_at"]) == (None, None)

    async def test_friends_see_online_status(
        self, alice_client, alice, bob, make_friendship, session_maker
    ) -> None:
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)
        async with session_maker() as db:
            (await db.get(User, bob.id)).is_online = True
            await db.commit()

        body = (await alice_client.get(f"/players/{uid(bob)}")).json()

        assert body["is_online"] is True

    async def test_a_pending_request_is_not_friendship(
        self, alice_client, alice, bob, make_friendship, session_maker
    ) -> None:
        await make_friendship(alice, bob, FriendshipStatus.PENDING)
        async with session_maker() as db:
            (await db.get(User, bob.id)).is_online = True
            await db.commit()

        assert (await alice_client.get(f"/players/{uid(bob)}")).json()[
            "is_online"
        ] is None

    async def test_you_see_your_own_status(self, alice_client, alice) -> None:
        body = (await alice_client.get(f"/players/{uid(alice)}")).json()

        assert body["is_online"] is False

    @pytest.mark.parametrize("blocker", ["viewer", "player"])
    async def test_a_block_either_way_hides_the_profile(
        self, alice_client, alice, bob, make_friendship, blocker
    ) -> None:
        first, second = (alice, bob) if blocker == "viewer" else (bob, alice)
        await make_friendship(first, second, FriendshipStatus.BLOCKED)

        response = await alice_client.get(f"/players/{uid(bob)}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Player not found"}

    async def test_unknown_player_is_not_found(self, alice_client) -> None:
        response = await alice_client.get(f"/players/{uuid.uuid4()}")

        assert response.status_code == 404

    async def test_invalid_id_is_rejected(self, alice_client) -> None:
        assert (await alice_client.get("/players/not-a-uuid")).status_code == 422

    async def test_requires_authentication(self, client, bob) -> None:
        assert (await client.get(f"/players/{uid(bob)}")).status_code == 401


class TestPlayerMatches:
    async def test_lists_their_matches_with_usernames(
        self, alice_client, bob, carol, session_maker
    ) -> None:
        await add_match(session_maker, bob, carol, MatchStatus.FINISHED, 1)

        body = (await alice_client.get(f"/players/{uid(bob)}/matches")).json()

        assert body["total"] == 1
        match = body["items"][0]
        assert (match["player1_username"], match["player2_username"]) == (
            "bob",
            "carol",
        )

    async def test_status_filter_and_pages(
        self, alice_client, bob, carol, session_maker
    ) -> None:
        for n, status in enumerate(
            [MatchStatus.FINISHED, MatchStatus.ABANDONED, MatchStatus.FINISHED], start=1
        ):
            await add_match(session_maker, bob, carol, status, n)

        body = (
            await alice_client.get(
                f"/players/{uid(bob)}/matches?status=FINISHED&size=1"
            )
        ).json()

        assert (body["total"], body["pages"], len(body["items"])) == (2, 2, 1)

    async def test_a_block_hides_the_matches_too(
        self, alice_client, alice, bob, make_friendship
    ) -> None:
        await make_friendship(bob, alice, FriendshipStatus.BLOCKED)

        response = await alice_client.get(f"/players/{uid(bob)}/matches")

        assert response.status_code == 404

    async def test_requires_authentication(self, client, bob) -> None:
        assert (await client.get(f"/players/{uid(bob)}/matches")).status_code == 401
