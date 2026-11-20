"""The database cleanup: one Elo rating in user_stats, stats rows for new
users, dropped tournament/AI/2FA-secret columns, Elo history on matches,
one cast per turn, and achievement word collections."""

import uuid

import pytest

pytest.importorskip(
    "backend.models.achievement_words",
    reason="The database cleanup is not merged into this branch",
)

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from backend.models import (
    Achievement,
    AchievementWord,
    Match,
    MatchCast,
    MatchStatus,
    User,
    UserAchievementWord,
    UserStats,
)
from backend.models.user_stats import DEFAULT_RATING


def uid(user: User) -> str:
    return str(uuid.UUID(bytes=user.id))


async def stats_of(session_maker, user_id: bytes) -> UserStats | None:
    async with session_maker() as session:
        return await session.get(UserStats, user_id)


class TestStatsForNewUsers:
    async def test_registering_creates_a_stats_row(self, client, session_maker):
        response = await client.post(
            "/auth/register",
            json={
                "username": "new_user",
                "email": "new@example.com",
                "password": "Sup3r-Secret!",
            },
        )
        assert response.status_code == 200

        stats = await stats_of(session_maker, uuid.UUID(response.json()["id"]).bytes)

        assert stats is not None
        assert stats.rating_elo == DEFAULT_RATING == 1200
        assert (stats.matches_played, stats.wins, stats.losses, stats.draws) == (
            0,
            0,
            0,
            0,
        )

    async def test_new_user_can_read_their_stats(self, make_client, client):
        await client.post(
            "/auth/register",
            json={
                "username": "new_user",
                "email": "new@example.com",
                "password": "Sup3r-Secret!",
            },
        )
        login = await client.post(
            "/auth/login",
            json={"email": "new@example.com", "password": "Sup3r-Secret!"},
        )
        assert login.status_code == 200
        client.headers["X-CSRF-Token"] = client.cookies["csrf_token"]

        response = await client.get(f"/users/{login.json()['id']}/stats")

        assert response.status_code == 200
        assert response.json()["rating_elo"] == 1200


class TestOneRating:
    async def test_users_have_no_elo_or_2fa_secret_column(self):
        columns = {column.name for column in User.__table__.columns}

        assert "elo" not in columns
        assert "two_factor_secret" not in columns

    async def test_queue_ticket_uses_the_stats_rating(self, make_user, login_as):
        client = await login_as(await make_user(elo=1475))

        response = await client.post(
            "/matchmaking/queue", json={"time_control_seconds": 180}
        )

        assert response.status_code == 201
        assert response.json()["elo"] == 1475

    async def test_user_without_stats_queues_at_the_starting_rating(self, alice_client):
        response = await alice_client.post(
            "/matchmaking/queue", json={"time_control_seconds": 180}
        )

        assert response.json()["elo"] == 1200

    async def test_status_of_an_active_match_shows_the_stats_rating(
        self, make_user, login_as, bob, session_maker
    ):
        alice = await make_user(elo=1333)
        async with session_maker() as session:
            session.add(
                Match(
                    id=uuid.uuid4().bytes,
                    player1_id=alice.id,
                    player2_id=bob.id,
                    time_control_seconds=180,
                    status=MatchStatus.ACTIVE,
                )
            )
            await session.commit()
        client = await login_as(alice)

        response = await client.get("/matchmaking/status")

        assert response.status_code == 200
        assert response.json()["status"] == "MATCHED"
        assert response.json()["elo"] == 1333

    async def test_leaderboard_columns_are_indexed(self):
        indexed = {
            tuple(column.name for column in index.columns)
            for index in UserStats.__table__.indexes
        }

        assert ("rating_elo",) in indexed
        assert ("wins",) in indexed


class TestMatches:
    async def test_tournament_and_ai_columns_are_gone(self):
        columns = {column.name for column in Match.__table__.columns}

        assert columns.isdisjoint(
            {"tournament_id", "tournament_round", "is_ai_match", "ai_difficulty"}
        )
        assert "tournaments" not in Match.metadata.tables
        assert "tournament_participants" not in Match.metadata.tables

    async def test_match_response_has_elo_history_and_no_dropped_fields(
        self, alice_client, alice, bob, session_maker
    ):
        match_id = uuid.uuid4().bytes
        async with session_maker() as session:
            session.add(
                Match(
                    id=match_id,
                    player1_id=alice.id,
                    player2_id=bob.id,
                    time_control_seconds=180,
                    status=MatchStatus.FINISHED,
                    winner_id=alice.id,
                    player1_elo_before=1200,
                    player1_elo_after=1216,
                    player2_elo_before=1200,
                    player2_elo_after=1184,
                )
            )
            await session.commit()

        response = await alice_client.get(f"/users/{uid(alice)}/matches")

        assert response.status_code == 200
        [match] = response.json()
        assert (
            match["player1_elo_before"],
            match["player1_elo_after"],
            match["player2_elo_before"],
            match["player2_elo_after"],
        ) == (1200, 1216, 1200, 1184)
        assert {"tournament_id", "is_ai_match", "ai_difficulty"}.isdisjoint(match)

    async def test_waiting_match_has_no_elo_history(
        self, alice_client, alice, session_maker
    ):
        async with session_maker() as session:
            session.add(
                Match(
                    id=uuid.uuid4().bytes,
                    player1_id=alice.id,
                    time_control_seconds=180,
                    status=MatchStatus.WAITING,
                )
            )
            await session.commit()

        [match] = (await alice_client.get(f"/users/{uid(alice)}/matches")).json()

        assert match["player2_id"] is None
        assert match["player1_elo_before"] is None
        assert match["player2_elo_after"] is None

    async def test_one_cast_per_turn(self, alice, bob, session_maker):
        match_id = uuid.uuid4().bytes

        def cast(turn: int) -> MatchCast:
            return MatchCast(
                match_id=match_id,
                turn_number=turn,
                player_id=alice.id,
                word_played="CAB",
                glyphs_payload={},
            )

        async with session_maker() as session:
            session.add(
                Match(
                    id=match_id,
                    player1_id=alice.id,
                    player2_id=bob.id,
                    time_control_seconds=180,
                    status=MatchStatus.ACTIVE,
                )
            )
            session.add_all([cast(1), cast(2)])
            await session.commit()

        async with session_maker() as session:
            session.add(cast(2))
            with pytest.raises(IntegrityError):
                await session.commit()


class TestAchievementWords:
    async def add_achievement(self, session_maker, *words: str) -> None:
        async with session_maker() as session:
            session.add(
                Achievement(
                    id="animals",
                    name="Animals",
                    description="Spell animal names",
                    icon_url="/static/animals.svg",
                )
            )
            await session.flush()
            session.add_all(
                AchievementWord(achievement_id="animals", word=w) for w in words
            )
            await session.commit()

    async def test_user_progress_must_name_a_collection_word(
        self, alice, session_maker
    ):
        await self.add_achievement(session_maker, "CAT", "DOG")

        async with session_maker() as session:
            session.add(
                UserAchievementWord(
                    user_id=alice.id, achievement_id="animals", word="CAT"
                )
            )
            await session.commit()

        async with session_maker() as session:
            session.add(
                UserAchievementWord(
                    user_id=alice.id, achievement_id="animals", word="COW"
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_progress_holds_every_word_of_a_collection(
        self, alice, bob, session_maker
    ):
        await self.add_achievement(session_maker, "CAT", "DOG")

        async with session_maker() as session:
            session.add_all(
                UserAchievementWord(user_id=user.id, achievement_id="animals", word=w)
                for user in (alice, bob)
                for w in ("CAT", "DOG")
            )
            await session.commit()

        async with session_maker() as session:
            rows = (await session.scalars(select(UserAchievementWord))).all()
        assert len(rows) == 4

    async def test_a_word_counts_once_per_user(self, alice, session_maker):
        await self.add_achievement(session_maker, "CAT")

        async with session_maker() as session:
            session.add(
                UserAchievementWord(
                    user_id=alice.id, achievement_id="animals", word="CAT"
                )
            )
            await session.commit()

        async with session_maker() as session:
            session.add(
                UserAchievementWord(
                    user_id=alice.id, achievement_id="animals", word="CAT"
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_deleting_an_achievement_removes_its_words_and_progress(
        self, alice, session_maker
    ):
        await self.add_achievement(session_maker, "CAT", "DOG")
        async with session_maker() as session:
            session.add(
                UserAchievementWord(
                    user_id=alice.id, achievement_id="animals", word="DOG"
                )
            )
            await session.commit()

        async with session_maker() as session:
            await session.execute(delete(Achievement))
            await session.commit()

        async with session_maker() as session:
            assert (await session.scalars(select(AchievementWord))).all() == []
            assert (await session.scalars(select(UserAchievementWord))).all() == []

    async def test_found_at_is_set(self, alice, session_maker):
        await self.add_achievement(session_maker, "CAT")
        async with session_maker() as session:
            row = UserAchievementWord(
                user_id=alice.id, achievement_id="animals", word="CAT"
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)

        assert row.found_at is not None


class TestMessages:
    async def test_bad_time_control_message_names_no_field(self, alice_client):
        response = await alice_client.post(
            "/matchmaking/queue", json={"time_control_seconds": 120}
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Time control must be 180, 300 or 600 seconds."
        }

    async def test_bad_lobby_time_control_message(self, alice_client):
        response = await alice_client.post(
            "/matchmaking/matches/custom", json={"time_control_seconds": 61}
        )

        assert response.json() == {
            "detail": "Time control must be 180, 300 or 600 seconds."
        }
