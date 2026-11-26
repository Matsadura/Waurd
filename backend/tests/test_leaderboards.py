"""Tests for GET /leaderboards?filter_by=."""

import uuid
from datetime import datetime

import pytest

from backend.models import Match, MatchCast, MatchStatus, User, UserStats


async def give_stats(session_maker, user: User, **values) -> None:  # type: ignore[no-untyped-def]
    async with session_maker() as session:
        session.add(UserStats(user_id=user.id, **values))
        await session.commit()


def names(response) -> list[str]:  # type: ignore[no-untyped-def]
    return [item["username"] for item in response.json()["items"]]


@pytest.fixture
async def players(make_user, session_maker, alice):  # type: ignore[no-untyped-def]
    """alice has no stats row; the others each lead one board."""
    leader = {
        "elo": await make_user(username="eloise"),
        "damage": await make_user(username="damon"),
        "streak": await make_user(username="stella"),
        "heal": await make_user(username="hector"),
    }
    await give_stats(
        session_maker, leader["elo"], rating_elo=1500, total_damage_dealt=10
    )
    await give_stats(
        session_maker, leader["damage"], rating_elo=1250, total_damage_dealt=900
    )
    await give_stats(
        session_maker, leader["streak"], best_win_streak=7, win_streak=3, wins=7
    )
    await give_stats(session_maker, leader["heal"], highest_heal=40, wins=1)
    return leader


class TestPlayerBoards:
    @pytest.mark.parametrize(
        ("filter_by", "first", "value"),
        [
            ("elo", "eloise", 1500),
            ("damage", "damon", 900),
            ("win_streak", "stella", 7),
            ("heal", "hector", 40),
        ],
    )
    async def test_each_board_ranks_on_its_stat(
        self, alice_client, players, filter_by, first, value
    ) -> None:
        response = await alice_client.get(f"/leaderboards?filter_by={filter_by}")

        assert response.status_code == 200
        body = response.json()
        assert body["filter_by"] == filter_by
        assert body["total"] == 5  # every player, alice included
        assert body["items"][0]["username"] == first
        assert body["items"][0]["value"] == value
        assert body["items"][0]["rank"] == 1

    async def test_elo_is_the_default(self, alice_client, players) -> None:
        response = await alice_client.get("/leaderboards")

        assert response.json()["filter_by"] == "elo"
        assert names(response)[0] == "eloise"

    async def test_a_player_without_stats_counts_as_new(
        self, alice_client, players
    ) -> None:
        body = (await alice_client.get("/leaderboards?filter_by=elo")).json()

        alice = next(i for i in body["items"] if i["username"] == "alice")
        assert (alice["value"], alice["matches_played"]) == (1200, 0)

    async def test_entries_have_the_player_fields(self, alice_client, players) -> None:
        body = (await alice_client.get("/leaderboards?filter_by=heal")).json()

        assert set(body["items"][0]) == {
            "rank",
            "user_id",
            "username",
            "avatar_url",
            "value",
            "matches_played",
        }

    async def test_ties_break_on_the_second_stat(
        self, alice_client, make_user, session_maker
    ) -> None:
        older = await make_user(username="older")
        newer = await make_user(username="newer")
        await give_stats(session_maker, older, best_win_streak=4, win_streak=0)
        await give_stats(session_maker, newer, best_win_streak=4, win_streak=4)

        response = await alice_client.get("/leaderboards?filter_by=win_streak")

        assert names(response)[:2] == ["newer", "older"]  # still on a run

    async def test_pages_keep_their_rank(self, alice_client, players) -> None:
        body = (
            await alice_client.get("/leaderboards?filter_by=damage&limit=2&offset=2")
        ).json()

        assert [i["rank"] for i in body["items"]] == [3, 4]
        assert (body["limit"], body["offset"], body["total"]) == (2, 2, 5)


class TestWordsBoard:
    async def test_words_lists_casts_from_finished_matches(
        self, alice_client, alice, bob, session_maker
    ) -> None:
        async with session_maker() as session:
            for status, word, damage in (
                (MatchStatus.FINISHED, "QUIZ", 40),
                (MatchStatus.ACTIVE, "LIVE", 99),  # not finished: left out
            ):
                match_id = uuid.uuid4().bytes
                session.add(
                    Match(
                        id=match_id,
                        player1_id=alice.id,
                        player2_id=bob.id,
                        time_control_seconds=180,
                        status=status,
                    )
                )
                session.add(
                    MatchCast(
                        match_id=match_id,
                        turn_number=1,
                        player_id=alice.id,
                        word_played=word,
                        damage_dealt=damage,
                        glyphs_payload={"glyphs": []},
                        created_at=datetime(2026, 1, 1),
                    )
                )
            await session.commit()

        body = (await alice_client.get("/leaderboards?filter_by=words")).json()

        assert body["filter_by"] == "words"
        assert [(i["word"], i["score"]) for i in body["items"]] == [("QUIZ", 40)]
        assert body["items"][0]["username"] == "alice"


class TestRequests:
    async def test_unknown_filter_is_rejected(self, alice_client) -> None:
        response = await alice_client.get("/leaderboards?filter_by=luck")

        assert response.status_code == 422

    async def test_requires_authentication(self, client) -> None:
        response = await client.get("/leaderboards")

        assert response.status_code == 401

    @pytest.mark.parametrize("old", ["elo", "words", "damage"])
    async def test_the_old_paths_are_gone(self, alice_client, old) -> None:
        response = await alice_client.get(f"/leaderboards/{old}")

        assert response.status_code == 404
