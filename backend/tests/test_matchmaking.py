"""Tests for the matchmaking queue, the matchmaker worker and custom lobbies.

Uses the fixtures in tests/conftest.py from the backend API test suite.
The queue's Lua scripts need fakeredis with Lua support (the lupa package).
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

# This suite lives on backend/api-tests, which may not contain matchmaking yet.
pytest.importorskip(
    "backend.core.matchmakerworker",
    reason="Matchmaking is not merged into this branch",
)
pytest.importorskip("lupa", reason="fakeredis needs lupa to run Lua scripts")

from sqlalchemy import select

from backend.core.matchmakerworker import MatchmakerWorker
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.models import Match, MatchStatus, User
from backend.repositories.match import MatchRepository


def uid(user: User) -> str:
    return str(uuid.UUID(bytes=user.id))


@pytest.fixture
def queue_store(redis) -> MatchmakingQueueStore:
    return MatchmakingQueueStore(redis)


@pytest.fixture
def worker(queue_store, session_maker) -> MatchmakerWorker:
    return MatchmakerWorker(queue_store=queue_store, session_factory=session_maker)


async def join(client, time_control: int = 180):
    return await client.post(
        "/matchmaking/queue", json={"time_control_seconds": time_control}
    )


async def leave(client, time_control: int = 180):
    return await client.request(
        "DELETE", "/matchmaking/queue", json={"time_control_seconds": time_control}
    )


async def create_lobby(client, time_control: int = 180):
    return await client.post(
        "/matchmaking/matches/custom", json={"time_control_seconds": time_control}
    )


async def matches(session_maker) -> list[Match]:
    async with session_maker() as session:
        return list((await session.scalars(select(Match))).all())


async def add_match(session_maker, player1: User, status=MatchStatus.WAITING, **kw):
    async with session_maker() as session:
        match = Match(
            id=uuid.uuid4().bytes,
            player1_id=player1.id,
            time_control_seconds=180,
            status=status,
            **kw,
        )
        session.add(match)
        await session.commit()
        await session.refresh(match)
    return match


class TestQueue:
    async def test_join(self, alice_client, alice):
        response = await join(alice_client)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "QUEUED"
        assert body["user_id"] == uid(alice)
        assert body["time_control_seconds"] == 180

    async def test_status_shows_the_ticket(self, alice_client):
        ticket = (await join(alice_client)).json()

        response = await alice_client.get("/matchmaking/status")

        assert response.status_code == 200
        assert response.json()["ticket_id"] == ticket["ticket_id"]

    async def test_joining_twice_keeps_one_ticket(self, alice_client, redis):
        first = (await join(alice_client)).json()
        second = (await join(alice_client)).json()

        assert first["ticket_id"] == second["ticket_id"]
        assert await redis.llen("matchmaking:queue:180") == 1

    async def test_switching_time_control(self, alice_client, alice, redis):
        await join(alice_client, 180)

        response = await join(alice_client, 600)

        assert response.json()["time_control_seconds"] == 600
        assert await redis.lrange("matchmaking:queue:180", 0, -1) == []
        assert await redis.lrange("matchmaking:queue:600", 0, -1) == [uid(alice)]

    @pytest.mark.parametrize("time_control", [0, 30, 60, 120, 900])
    async def test_invalid_time_control(self, alice_client, time_control):
        assert (await join(alice_client, time_control)).status_code == 422

    @pytest.mark.parametrize("time_control", [180, 300, 600])
    async def test_every_time_control_can_queue(self, alice_client, time_control):
        assert (await join(alice_client, time_control)).status_code == 201

    async def test_custom_lobby_defaults_to_five_minutes(self, alice_client):
        response = await alice_client.post("/matchmaking/matches/custom", json={})

        assert response.status_code == 201
        assert response.json()["time_control_seconds"] == 300

    async def test_worker_checks_every_time_control(self, queue_store, session_maker):
        worker = MatchmakerWorker(
            queue_store=queue_store, session_factory=session_maker
        )
        assert worker.time_controls == [180, 300, 600]

    async def test_leave(self, alice_client, redis):
        await join(alice_client)

        response = await leave(alice_client)

        assert response.status_code == 200
        assert (await alice_client.get("/matchmaking/status")).status_code == 404
        assert await redis.llen("matchmaking:queue:180") == 0

    async def test_leave_when_not_queued(self, alice_client):
        assert (await leave(alice_client)).status_code == 404

    async def test_leave_with_other_time_control(self, alice_client):
        await join(alice_client, 180)

        assert (await leave(alice_client, 600)).status_code == 404

    async def test_cannot_queue_with_an_open_lobby(self, alice_client):
        await create_lobby(alice_client)

        response = await join(alice_client)

        assert response.status_code == 400

    async def test_requires_csrf(self, alice_client):
        del alice_client.headers["X-CSRF-Token"]

        assert (await join(alice_client)).status_code == 403

    async def test_requires_authentication(self, anon_with_csrf):
        assert (await join(anon_with_csrf)).status_code == 401


class TestWorker:
    async def test_pairs_two_players(
        self, alice_client, bob_client, alice, bob, worker, session_maker
    ):
        await join(alice_client)
        await join(bob_client)

        await worker.process_queue_for_time_control(180)

        [match] = await matches(session_maker)
        assert match.status == MatchStatus.ACTIVE
        assert {match.player1_id, match.player2_id} == {alice.id, bob.id}
        for client in (alice_client, bob_client):
            status = (await client.get("/matchmaking/status")).json()
            assert status["status"] == "MATCHED"
            assert status["matched_match_id"] == str(uuid.UUID(bytes=match.id))

    async def test_queue_matches_record_their_start(
        self, alice_client, bob_client, worker, session_maker
    ):
        await join(alice_client)
        await join(bob_client)

        await worker.process_queue_for_time_control(180)

        [match] = await matches(session_maker)
        assert match.started_at is not None

    async def test_far_apart_ratings_are_not_paired(
        self, make_user, login_as, worker, session_maker
    ):
        for elo in (100, 900):
            await join(await login_as(await make_user(elo=elo)))

        await worker.process_queue_for_time_control(180)

        assert await matches(session_maker) == []

    async def test_close_neighbours_are_not_starved(
        self, make_user, login_as, worker, session_maker
    ):
        # Sorted: 100, 500, 520. 100 can't play 500, but 500 and 520 can.
        users = [await make_user(elo=elo) for elo in (100, 500, 520)]
        for user in users:
            await join(await login_as(user))

        await worker.process_queue_for_time_control(180)

        [match] = await matches(session_maker)
        assert {match.player1_id, match.player2_id} == {users[1].id, users[2].id}

    async def test_never_pairs_a_player_with_themselves(
        self, alice_client, alice, redis, worker, session_maker
    ):
        await join(alice_client)
        # A stale entry left behind when a ticket expired and the user rejoined.
        await redis.rpush("matchmaking:queue:180", uid(alice))

        await worker.process_queue_for_time_control(180)

        assert await matches(session_maker) == []
        status = (await alice_client.get("/matchmaking/status")).json()
        assert status["status"] == "QUEUED"

    async def test_failed_save_returns_players_to_the_queue(
        self, alice_client, bob_client, worker, session_maker, monkeypatch
    ):
        await join(alice_client)
        await join(bob_client)

        async def broken(*_args, **_kwargs):
            raise RuntimeError("database unavailable")

        monkeypatch.setattr(MatchRepository, "create_pvp_match", broken)
        await worker.process_queue_for_time_control(180)
        monkeypatch.undo()

        for client in (alice_client, bob_client):
            assert (await client.get("/matchmaking/status")).json()[
                "status"
            ] == "QUEUED"

        await worker.process_queue_for_time_control(180)
        assert len(await matches(session_maker)) == 1

    async def test_time_controls_are_separate(
        self, alice_client, bob_client, worker, session_maker
    ):
        assert (await join(alice_client, 600)).status_code == 201
        assert (await join(bob_client, 180)).status_code == 201

        for time_control in (180, 300, 600):
            await worker.process_queue_for_time_control(time_control)

        assert await matches(session_maker) == []

    async def test_left_players_are_not_paired(
        self, alice_client, bob_client, worker, session_maker
    ):
        await join(alice_client)
        await join(bob_client)
        await leave(bob_client)

        await worker.process_queue_for_time_control(180)

        assert await matches(session_maker) == []


class TestLobbies:
    async def test_create(self, alice_client, alice):
        response = await create_lobby(alice_client)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "WAITING"
        assert len(body["invite_code"]) == 6
        assert body["creator"]["id"] == uid(alice)

    async def test_cannot_create_while_queued(self, alice_client):
        await join(alice_client)

        response = await create_lobby(alice_client)

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Please leave the matchmaking queue first."
        }

    async def test_join_by_code(self, alice_client, bob_client, alice):
        code = (await create_lobby(alice_client)).json()["invite_code"]

        response = await bob_client.post(
            "/matchmaking/matches/join", json={"invite_code": code.lower()}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ACTIVE"
        assert response.json()["creator"]["id"] == uid(alice)
        details = await bob_client.get(f"/matchmaking/matches/{response.json()['id']}")
        assert details.json()["started_at"] is not None

    async def test_lobby_takes_one_opponent(
        self, alice_client, bob_client, carol_client
    ):
        code = (await create_lobby(alice_client)).json()["invite_code"]
        await bob_client.post("/matchmaking/matches/join", json={"invite_code": code})

        response = await carol_client.post(
            "/matchmaking/matches/join", json={"invite_code": code}
        )

        assert response.status_code == 400

    async def test_unknown_code(self, bob_client):
        response = await bob_client.post(
            "/matchmaking/matches/join", json={"invite_code": "ZZZZZZ"}
        )

        assert response.status_code == 404

    async def test_old_lobby_expires(self, alice, bob_client, session_maker):
        await add_match(
            session_maker,
            alice,
            invite_code="OLDOLD",
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=20),
        )

        response = await bob_client.post(
            "/matchmaking/matches/join", json={"invite_code": "OLDOLD"}
        )

        assert response.status_code == 404

    async def test_ticket_of_a_finished_match_does_not_block(
        self, alice_client, alice, redis
    ):
        # E.g. a match that ended some other way than the abandon endpoint.
        ticket = {
            "ticket_id": "t",
            "user_id": uid(alice),
            "time_control_seconds": 180,
            "elo": 1,
            "status": "MATCHED",
            "queued_at": "2026-01-01T00:00:00+00:00",
            "matched_match_id": "old",
        }
        await redis.set(f"matchmaking:user:{uid(alice)}", json.dumps(ticket))

        assert (await create_lobby(alice_client)).status_code == 201

    async def test_cannot_join_while_queued(self, alice_client, bob_client):
        code = (await create_lobby(alice_client)).json()["invite_code"]
        await join(bob_client)

        response = await bob_client.post(
            "/matchmaking/matches/join", json={"invite_code": code}
        )

        assert response.status_code == 400

    async def test_cancel(self, alice_client, session_maker):
        lobby = (await create_lobby(alice_client)).json()

        response = await alice_client.delete(f"/matchmaking/matches/{lobby['id']}")

        assert response.status_code == 200
        [match] = await matches(session_maker)
        assert match.status == MatchStatus.ABANDONED
        assert (await create_lobby(alice_client)).status_code == 201

    async def test_only_the_creator_can_cancel(self, alice_client, bob_client):
        lobby = (await create_lobby(alice_client)).json()

        response = await bob_client.delete(f"/matchmaking/matches/{lobby['id']}")

        assert response.status_code == 403

    async def test_open_lobby_does_not_break_match_history(self, alice_client, alice):
        await create_lobby(alice_client)

        response = await alice_client.get(f"/users/{uid(alice)}/matches")

        assert response.status_code == 200
        [match] = response.json()["items"]
        assert match["player2_id"] is None

    async def test_duplicate_open_lobbies_do_not_break_status(
        self, alice_client, alice, session_maker
    ):
        # Two lobbies can exist after a double-click races the "already
        # hosting" check.
        await add_match(session_maker, alice, invite_code="AAAAAA")
        await add_match(session_maker, alice, invite_code="BBBBBB")

        response = await alice_client.get("/matchmaking/status")

        assert response.status_code == 200
        assert response.json()["status"] == "WAITING"


class TestMatchDetails:
    async def test_creator_sees_the_invite_code(self, alice_client):
        lobby = (await create_lobby(alice_client)).json()

        response = await alice_client.get(f"/matchmaking/matches/{lobby['id']}")

        assert response.status_code == 200
        assert response.json()["invite_code"] == lobby["invite_code"]

    async def test_others_do_not_see_the_invite_code(self, alice_client, bob_client):
        lobby = (await create_lobby(alice_client)).json()

        response = await bob_client.get(f"/matchmaking/matches/{lobby['id']}")

        assert response.status_code == 200
        assert response.json()["invite_code"] is None

    async def test_invalid_id(self, alice_client):
        response = await alice_client.get("/matchmaking/matches/not-a-uuid")

        assert response.status_code == 400

    async def test_unknown_match(self, alice_client):
        response = await alice_client.get(f"/matchmaking/matches/{uuid.uuid4()}")

        assert response.status_code == 404

    async def test_casts_of_an_ongoing_match_are_private(
        self, carol_client, alice, bob, session_maker
    ):
        match = await add_match(
            session_maker, alice, status=MatchStatus.ACTIVE, player2_id=bob.id
        )

        response = await carol_client.get(
            f"/matchmaking/matches/{uuid.UUID(bytes=match.id)}/casts"
        )

        assert response.status_code == 403


class TestAbandon:
    async def queue_match(self, alice_client, bob_client, worker) -> str:
        await join(alice_client)
        await join(bob_client)
        await worker.process_queue_for_time_control(180)
        return (await alice_client.get("/matchmaking/status")).json()[
            "matched_match_id"
        ]

    async def test_abandon(self, alice_client, bob_client, worker, session_maker):
        match_id = await self.queue_match(alice_client, bob_client, worker)

        response = await alice_client.delete(f"/matchmaking/matches/{match_id}/abandon")

        assert response.status_code == 200
        [match] = await matches(session_maker)
        assert match.status == MatchStatus.ABANDONED
        assert match.ended_at is not None

    async def test_both_players_can_queue_again_right_away(
        self, alice_client, bob_client, worker
    ):
        match_id = await self.queue_match(alice_client, bob_client, worker)
        await alice_client.delete(f"/matchmaking/matches/{match_id}/abandon")

        assert (await join(alice_client)).status_code == 201
        assert (await create_lobby(bob_client)).status_code == 201

    async def test_status_after_abandon_is_not_the_old_match(
        self, alice_client, bob_client, worker
    ):
        match_id = await self.queue_match(alice_client, bob_client, worker)
        await alice_client.delete(f"/matchmaking/matches/{match_id}/abandon")

        response = await bob_client.get("/matchmaking/status")

        assert response.status_code == 404

    async def test_only_players_can_abandon(
        self, alice_client, bob_client, carol_client, worker
    ):
        match_id = await self.queue_match(alice_client, bob_client, worker)

        response = await carol_client.delete(f"/matchmaking/matches/{match_id}/abandon")

        assert response.status_code == 403

    async def test_waiting_lobby_cannot_be_abandoned(self, alice_client):
        lobby = (await create_lobby(alice_client)).json()

        response = await alice_client.delete(
            f"/matchmaking/matches/{lobby['id']}/abandon"
        )

        assert response.status_code == 400
