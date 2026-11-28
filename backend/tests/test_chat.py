"""Chat: one socket per user for global, direct and match messages, plus history."""

import asyncio
import threading
import time
import uuid

import pytest
from anyio.from_thread import start_blocking_portal

chat_ws = pytest.importorskip("backend.ws.chat_ws", reason="Chat is not merged yet")

from fastapi import WebSocketDisconnect
from starlette.testclient import TestClient

from backend.main import app
from backend.models import (
    ChannelType,
    ChatMessage,
    FriendshipStatus,
    Match,
    MatchStatus,
    User,
)

ORIGIN = "http://localhost:5173"


def uid(user) -> str:  # type: ignore[no-untyped-def]
    return str(uuid.UUID(bytes=user.id))


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch, session_maker):  # type: ignore[no-untyped-def]
    chat_ws.sockets.clear()
    monkeypatch.setattr(chat_ws, "async_session_maker", session_maker)
    # a lock belongs to the event loop that first uses it, and each test has its own
    monkeypatch.setattr(chat_ws, "presence_lock", asyncio.Lock())


@pytest.fixture
def client(monkeypatch):  # type: ignore[no-untyped-def]
    """The logged-in user is named by an x-user header holding their id."""

    async def user(ws):  # type: ignore[no-untyped-def]
        return ws.headers.get("x-user")

    monkeypatch.setattr(chat_ws, "user_id_from_cookie", user)
    monkeypatch.setattr(chat_ws.settings, "CORS_ORIGINS", [ORIGIN])
    test_client = TestClient(app)
    # One event loop for every socket, as on the server; otherwise a message
    # sent to another socket doesn't wake that socket's reader.
    with start_blocking_portal() as portal:
        test_client.portal = portal
        yield test_client


def connect(client, user):  # type: ignore[no-untyped-def]
    return client.websocket_connect(
        "/ws/chat", headers={"origin": ORIGIN, "x-user": uid(user)}
    )


def receive(socket) -> dict:  # type: ignore[no-untyped-def]
    """The socket's next message; fails instead of hanging if none comes."""
    result: dict = {}
    reader = threading.Thread(
        target=lambda: result.setdefault("message", socket.receive_json()), daemon=True
    )
    reader.start()
    reader.join(2)
    assert "message" in result, "no message arrived"
    return result["message"]


def wait_until(condition, seconds: float = 2.0) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


def online(count: int) -> None:
    """Wait until the server has registered that many users' sockets."""
    deadline = time.monotonic() + 2
    while len(chat_ws.sockets) < count:
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


async def add_match(session_maker, player1, player2) -> str:  # type: ignore[no-untyped-def]
    match_id = uuid.uuid4()
    async with session_maker() as db:
        db.add(
            Match(
                id=match_id.bytes,
                player1_id=player1.id,
                player2_id=player2.id,
                time_control_seconds=180,
                status=MatchStatus.ACTIVE,
            )
        )
        await db.commit()
    return str(match_id)


class TestChatSocket:
    def test_global_reaches_everyone_online(self, client, alice, bob) -> None:  # type: ignore[no-untyped-def]
        with connect(client, alice) as a, connect(client, bob) as b:
            online(2)
            a.send_json({"type": "GLOBAL", "text": "  hello all  "})

            for socket in (a, b):
                message = receive(socket)
                assert message["type"] == "CHAT_MESSAGE"
                assert message["channel"] == "GLOBAL"
                assert (message["sender_username"], message["text"]) == (
                    "alice",
                    "hello all",
                )

    def test_direct_reaches_only_the_two_players(
        self, client, alice, bob, carol
    ) -> None:  # type: ignore[no-untyped-def]
        with (
            connect(client, alice) as a,
            connect(client, bob) as b,
            connect(client, carol) as c,
        ):
            online(3)
            a.send_json({"type": "DIRECT", "to": uid(bob), "text": "hi bob"})

            assert receive(b)["receiver_id"] == uid(bob)
            assert receive(a)["text"] == "hi bob"  # the sender's other tabs see it too
            c.send_json({"type": "GLOBAL", "text": "ping"})
            assert receive(c)["text"] == "ping"  # carol got nothing before this

    def test_a_block_stops_direct_messages(
        self, client, alice, bob, make_friendship
    ) -> None:  # type: ignore[no-untyped-def]
        import asyncio

        asyncio.run(make_friendship(bob, alice, FriendshipStatus.BLOCKED))
        with connect(client, alice) as a:
            a.send_json({"type": "DIRECT", "to": uid(bob), "text": "hey"})

            assert receive(a) == {
                "type": "CHAT_REJECTED",
                "reason": "You can't message this player.",
            }

    def test_match_chat_is_for_its_players_only(
        self, client, alice, bob, carol, session_maker
    ) -> None:  # type: ignore[no-untyped-def]
        import asyncio

        match_id = asyncio.run(add_match(session_maker, alice, bob))
        with connect(client, bob) as b, connect(client, carol) as c:
            online(2)
            c.send_json({"type": "MATCH", "match_id": match_id, "text": "gg"})
            assert receive(c)["reason"] == "You're not a player in this match."

            b.send_json({"type": "MATCH", "match_id": match_id, "text": "gg"})
            message = receive(b)
            assert (message["channel"], message["match_id"]) == ("MATCH", match_id)

    def test_bad_messages_are_rejected_and_the_socket_stays_open(
        self, client, alice
    ) -> None:  # type: ignore[no-untyped-def]
        with connect(client, alice) as a:
            for bad in (
                [1, 2],
                {"type": "SHOUT", "text": "hi"},
                {"type": "GLOBAL"},
                {"type": "GLOBAL", "text": "   "},
                {"type": "GLOBAL", "text": "x" * 501},
                {"type": "DIRECT", "to": "not-an-id", "text": "hi"},
                {"type": "DIRECT", "to": uid(alice), "text": "talking to myself"},
                {"type": "MATCH", "match_id": str(uuid.uuid4()), "text": "hi"},
            ):
                a.send_json(bad)
                assert receive(a)["type"] == "CHAT_REJECTED", bad

            a.send_json({"type": "GLOBAL", "text": "still here"})
            assert receive(a)["text"] == "still here"

    def test_without_a_session_the_socket_is_refused(self, client) -> None:  # type: ignore[no-untyped-def]
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect("/ws/chat", headers={"origin": ORIGIN}) as ws,
        ):
            ws.receive_json()


def presence(session_maker, user):  # type: ignore[no-untyped-def]
    """(is_online, last_seen_at) as stored for the user."""

    async def read():  # type: ignore[no-untyped-def]
        async with session_maker() as db:
            row = await db.get(User, user.id)
            return row.is_online, row.last_seen_at

    return asyncio.run(read())


class TestOnlineStatus:
    def test_online_while_any_tab_is_open(self, client, alice, session_maker) -> None:  # type: ignore[no-untyped-def]
        with connect(client, alice):
            online(1)
            wait_until(lambda: presence(session_maker, alice)[0])
            tabs = lambda: len(chat_ws.sockets.get(uid(alice), ()))  # noqa: E731
            with connect(client, alice):  # a second tab
                wait_until(lambda: tabs() == 2)
            wait_until(lambda: tabs() == 1)  # the server handled the close
            assert presence(session_maker, alice) == (True, None)  # one tab still open

        wait_until(lambda: not presence(session_maker, alice)[0])
        assert presence(session_maker, alice)[1] is not None  # last seen just now

    def test_friends_see_who_is_online(
        self, client, alice, bob, make_friendship, alice_client, session_maker
    ) -> None:  # type: ignore[no-untyped-def]
        asyncio.run(make_friendship(alice, bob, FriendshipStatus.ACCEPTED))
        with connect(client, bob):
            wait_until(lambda: presence(session_maker, bob)[0])

            friends = asyncio.run(alice_client.get("/friends")).json()["items"]

        assert [(f["username"], f["is_online"]) for f in friends] == [("bob", True)]

    async def test_a_restart_sets_everyone_offline(self, alice, session_maker) -> None:
        async with session_maker() as db:
            (await db.get(User, alice.id)).is_online = True
            await db.commit()

        await chat_ws.reset_online_status()

        async with session_maker() as db:
            row = await db.get(User, alice.id)
        assert (row.is_online, row.last_seen_at is not None) == (False, True)


async def add_messages(session_maker, *messages) -> None:  # type: ignore[no-untyped-def]
    async with session_maker() as db:
        db.add_all(messages)
        await db.commit()


class TestChatHistory:
    async def test_direct_history_is_both_ways_newest_first(
        self, alice_client, alice, bob, carol, session_maker
    ) -> None:
        await add_messages(
            session_maker,
            ChatMessage(
                sender_id=alice.id,
                receiver_id=bob.id,
                channel_type=ChannelType.DIRECT,
                message_content="one",
            ),
            ChatMessage(
                sender_id=bob.id,
                receiver_id=alice.id,
                channel_type=ChannelType.DIRECT,
                message_content="two",
            ),
            ChatMessage(
                sender_id=carol.id,
                receiver_id=alice.id,
                channel_type=ChannelType.DIRECT,
                message_content="other chat",
            ),
        )

        page = (await alice_client.get(f"/chat/direct/{uid(bob)}?size=1")).json()
        second = (
            await alice_client.get(f"/chat/direct/{uid(bob)}?size=1&page=2")
        ).json()

        assert (page["total"], page["pages"]) == (2, 2)
        assert [page["items"][0]["text"], second["items"][0]["text"]] == ["two", "one"]
        assert page["items"][0]["sender_username"] == "bob"

    async def test_global_history(self, alice_client, bob, session_maker) -> None:
        await add_messages(
            session_maker,
            ChatMessage(
                sender_id=bob.id,
                channel_type=ChannelType.GLOBAL,
                message_content="hello",
            ),
        )

        page = (await alice_client.get("/chat/global")).json()

        assert [(m["sender_username"], m["text"]) for m in page["items"]] == [
            ("bob", "hello")
        ]

    async def test_match_history_is_for_its_players_only(
        self, alice_client, carol_client, alice, bob, session_maker
    ) -> None:
        match_id = await add_match(session_maker, alice, bob)
        await add_messages(
            session_maker,
            ChatMessage(
                sender_id=bob.id,
                channel_type=ChannelType.MATCH,
                match_id=uuid.UUID(match_id).bytes,
                message_content="gg",
            ),
        )

        mine = await alice_client.get(f"/chat/matches/{match_id}")
        theirs = await carol_client.get(f"/chat/matches/{match_id}")

        assert [m["text"] for m in mine.json()["items"]] == ["gg"]
        assert theirs.status_code == 403
        assert (
            await alice_client.get(f"/chat/matches/{uuid.uuid4()}")
        ).status_code == 404


def no_message(socket, seconds: float = 0.3) -> bool:  # type: ignore[no-untyped-def]
    """True if nothing arrives on the socket for a short while."""
    result: dict = {}
    reader = threading.Thread(
        target=lambda: result.setdefault("message", socket.receive_json()), daemon=True
    )
    reader.start()
    reader.join(seconds)
    return "message" not in result


def log_in(client, user) -> dict:  # type: ignore[no-untyped-def]
    """Log the test client in (same event loop as the sockets); returns the CSRF header."""
    from conftest import PASSWORD

    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": client.cookies["csrf_token"]}


class TestNotifications:
    def test_the_recipient_hears_about_a_new_friend_request(
        self, client, alice, bob
    ) -> None:  # type: ignore[no-untyped-def]
        csrf = log_in(client, alice)
        with connect(client, bob) as bob_ws:
            online(1)

            sent = client.post(
                "/api/v1/friends/requests", json={"username": "bob"}, headers=csrf
            ).json()

            assert receive(bob_ws) == {
                "type": "SOCIAL_NOTIFICATION",
                "kind": "FRIEND_REQUEST",
                "request_id": sent["id"],
                "user": {"id": uid(alice), "username": "alice", "avatar_url": None},
            }

    def test_the_sender_hears_when_it_is_accepted(
        self, client, alice, bob, make_friendship
    ) -> None:  # type: ignore[no-untyped-def]
        request = asyncio.run(make_friendship(alice, bob, FriendshipStatus.PENDING))
        csrf = log_in(client, bob)
        with connect(client, alice) as alice_ws:
            online(1)

            client.patch(
                f"/api/v1/friends/requests/{request.id}",
                json={"action": "ACCEPTED"},
                headers=csrf,
            )

            message = receive(alice_ws)
        assert (
            message["kind"],
            message["request_id"],
            message["user"]["username"],
        ) == (
            "FRIEND_ACCEPTED",
            request.id,
            "bob",
        )

    def test_a_declined_request_sends_nothing(
        self, client, alice, bob, make_friendship
    ) -> None:  # type: ignore[no-untyped-def]
        request = asyncio.run(make_friendship(alice, bob, FriendshipStatus.PENDING))
        csrf = log_in(client, bob)
        with connect(client, alice) as alice_ws:
            online(1)

            client.patch(
                f"/api/v1/friends/requests/{request.id}",
                json={"action": "DECLINED"},
                headers=csrf,
            )

            assert no_message(alice_ws)

    def test_friends_hear_when_you_come_online_and_leave(
        self, client, alice, bob, make_friendship
    ) -> None:  # type: ignore[no-untyped-def]
        asyncio.run(make_friendship(alice, bob, FriendshipStatus.ACCEPTED))
        with connect(client, alice) as alice_ws:
            online(1)
            with connect(client, bob):
                came = receive(alice_ws)
            left = receive(alice_ws)

        assert came == {
            "type": "PRESENCE_UPDATE",
            "user_id": uid(bob),
            "is_online": True,
            "last_seen_at": None,
        }
        assert (left["user_id"], left["is_online"]) == (uid(bob), False)
        assert left["last_seen_at"] is not None

    def test_only_friends_hear_it(
        self, client, alice, bob, carol, make_friendship
    ) -> None:  # type: ignore[no-untyped-def]
        asyncio.run(make_friendship(alice, bob, FriendshipStatus.PENDING))
        with connect(client, alice) as alice_ws, connect(client, carol) as carol_ws:
            online(2)
            with connect(client, bob):
                online(3)
                assert no_message(alice_ws)  # only a pending request
                assert no_message(carol_ws)  # a stranger

    def test_a_second_tab_does_not_announce_again(
        self, client, alice, bob, make_friendship
    ) -> None:  # type: ignore[no-untyped-def]
        asyncio.run(make_friendship(alice, bob, FriendshipStatus.ACCEPTED))
        with connect(client, alice) as alice_ws, connect(client, bob):
            online(2)
            assert receive(alice_ws)["is_online"] is True
            with connect(client, bob):  # bob opens another tab
                wait_until(lambda: len(chat_ws.sockets[uid(bob)]) == 2)
                assert no_message(alice_ws)


async def test_accepted_friend_ids_cover_both_directions(
    session_maker, alice, bob, carol, make_user, make_friendship
) -> None:
    from backend.repositories.friendship import FriendshipRepository

    dave = await make_user(username="dave")
    await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)
    await make_friendship(carol, alice, FriendshipStatus.ACCEPTED)
    await make_friendship(alice, dave, FriendshipStatus.PENDING)

    async with session_maker() as db:
        ids = await FriendshipRepository(db).accepted_friend_ids(alice.id)

    assert set(ids) == {bob.id, carol.id}
