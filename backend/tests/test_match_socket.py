"""The match socket endpoint: who may connect, and messages reaching the hub."""

import asyncio
import uuid

import pytest

pytest.importorskip("backend.live.hub", reason="Live matches are not merged yet")

import fakeredis
from backend.live.hub import MatchAccessError
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.core.config import settings
from backend.core.session_store import RedisSessionStore
from backend.main import app

MATCH = str(uuid.uuid4())
USER = str(uuid.uuid4())
PATH = f"/api/v1/ws/matches/{MATCH}"


class StubHub:
    def __init__(self, error: MatchAccessError | None = None) -> None:
        self.error = error
        self.connected: list[tuple[str, str]] = []
        self.received: list[object] = []
        self.disconnected = 0

    async def connect(self, match_id, user_id, send):  # type: ignore[no-untyped-def]
        if self.error:
            raise self.error
        self.connected.append((match_id, user_id))
        await send({"type": "MATCH_STATE", "data": {}, "seq": 1})
        return "connection"

    async def receive(self, connection, message):  # type: ignore[no-untyped-def]
        self.received.append(message)

    async def disconnect(self, connection):  # type: ignore[no-untyped-def]
        self.disconnected += 1


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """A fake Redis with one signed-in user; returns (client, hub, session id)."""
    monkeypatch.setattr(
        settings, "CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    fake = fakeredis.FakeServer()
    session_id = asyncio.run(
        RedisSessionStore(
            fakeredis.FakeAsyncRedis(server=fake, decode_responses=True), 600
        ).create_session(USER)
    )
    hub = StubHub()
    before = (getattr(app.state, "redis", None), getattr(app.state, "match_hub", None))
    app.state.redis = fakeredis.FakeAsyncRedis(server=fake, decode_responses=True)
    app.state.match_hub = hub
    yield TestClient(app), hub, session_id
    app.state.redis, app.state.match_hub = before


def cookies(session_id: str) -> dict[str, str]:
    return {"cookie": f"{settings.SESSION_COOKIE_NAME}={session_id}"}


def test_connects_and_passes_messages(server) -> None:  # type: ignore[no-untyped-def]
    client, hub, session_id = server

    with client.websocket_connect(PATH, headers=cookies(session_id)) as socket:
        assert socket.receive_json()["type"] == "MATCH_STATE"
        socket.send_json({"type": "PING", "data": {"ts": 1}})
        socket.send_text("not json")
        assert socket.receive_json() == {
            "type": "ERROR",
            "data": {"code": "INVALID_JSON", "detail": "Send JSON."},
        }

    assert hub.connected == [(MATCH, USER)]
    assert hub.received == [{"type": "PING", "data": {"ts": 1}}]
    assert hub.disconnected == 1


def test_match_id_is_normalized(server) -> None:  # type: ignore[no-untyped-def]
    client, hub, session_id = server

    with client.websocket_connect(
        f"/api/v1/ws/matches/{MATCH.upper()}", headers=cookies(session_id)
    ) as socket:
        socket.receive_json()

    assert hub.connected == [(MATCH, USER)]


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_frontend_origins_are_allowed(server, origin: str) -> None:  # type: ignore[no-untyped-def]
    client, hub, session_id = server

    with client.websocket_connect(
        PATH, headers={**cookies(session_id), "origin": origin}
    ) as socket:
        socket.receive_json()

    assert hub.connected


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        (PATH, {}),  # no session cookie
        (PATH, {"cookie": f"{settings.SESSION_COOKIE_NAME}=nope"}),  # unknown session
        ("/api/v1/ws/matches/not-a-uuid", None),
        (PATH, {"origin": "https://evil.example"}),
    ],
    ids=["no-cookie", "bad-session", "bad-id", "bad-origin"],
)
def test_refused_connections(server, path: str, headers) -> None:  # type: ignore[no-untyped-def]
    client, hub, session_id = server
    if headers is None:
        headers = cookies(session_id)
    elif "origin" in headers:
        headers = {**cookies(session_id), **headers}

    with (
        pytest.raises(WebSocketDisconnect) as caught,
        client.websocket_connect(path, headers=headers) as socket,
    ):
        socket.receive_json()

    assert caught.value.code == 1008
    assert hub.connected == []


def test_hub_refusal_closes_with_the_reason(server) -> None:  # type: ignore[no-untyped-def]
    client, hub, session_id = server
    hub.error = MatchAccessError("You are not a player in this match", 403)

    with (
        pytest.raises(WebSocketDisconnect) as caught,
        client.websocket_connect(PATH, headers=cookies(session_id)) as socket,
    ):
        socket.receive_json()

    assert caught.value.code == 1008
    assert caught.value.reason == "You are not a player in this match"
