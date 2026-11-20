"""End to end against a running backend: two players get paired and play a
whole match over the real match socket.

Runs only when WAURD_E2E_URL points at a server, e.g.

    WAURD_E2E_URL=http://127.0.0.1:8001 uv run pytest tests/e2e
"""

import asyncio
import json
import os
import uuid

import pytest

BASE = os.environ.get("WAURD_E2E_URL")
pytestmark = pytest.mark.skipif(
    not BASE, reason="Set WAURD_E2E_URL to a running backend"
)

httpx = pytest.importorskip("httpx")
websockets = pytest.importorskip("websockets")
pytest.importorskip(
    "backend.game.simulation", reason="Needs the engine for the bots' word finder"
)

from backend.core.dictionary import load_word_list
from backend.game.simulation import WordFinder
from backend.game.state import Glyph

FINDER = WordFinder(load_word_list()) if BASE else None


class Bot:
    def __init__(self, http, user_id: str) -> None:  # type: ignore[no-untyped-def]
        self.http = http
        self.id = user_id
        self.ended: dict | None = None
        self.casts = 0
        self.passes = 0

    @classmethod
    async def sign_up(cls, name: str) -> "Bot":
        http = httpx.AsyncClient(base_url=f"{BASE}/api/v1", timeout=10)
        email = f"{name}@example.com"
        registered = await http.post(
            "/auth/register",
            json={"username": name, "email": email, "password": "Sup3r-Secret!"},
        )
        assert registered.status_code == 200, registered.text
        login = await http.post(
            "/auth/login", json={"email": email, "password": "Sup3r-Secret!"}
        )
        assert login.status_code == 200, login.text
        return cls(http, login.json()["id"])

    def csrf(self) -> dict[str, str]:
        return {"X-CSRF-Token": self.http.cookies["csrf_token"]}

    async def play(self, match_id: str) -> None:
        url = BASE.replace("http", "ws") + f"/api/v1/ws/matches/{match_id}"  # type: ignore[union-attr]
        cookie = f"session_id={self.http.cookies['session_id']}"
        async with websockets.connect(
            url, additional_headers={"Cookie": cookie}
        ) as socket:
            ready_sent = False
            async for raw in socket:
                message = json.loads(raw)
                kind, data = message["type"], message["data"]
                if kind == "MATCH_ENDED":
                    self.ended = data
                    return
                if kind == "ACTION_REJECTED":
                    raise AssertionError(f"rejected: {data}")
                if kind != "MATCH_STATE":
                    continue
                me = next(p for p in data["players"] if p["id"] == self.id)
                if data["phase"] == "WAITING" and not me["ready"] and not ready_sent:
                    ready_sent = True  # once: a second snapshot may come first
                    await socket.send(json.dumps({"type": "PLAYER_READY", "data": {}}))
                if data["active_player_id"] != self.id:
                    continue
                if data["phase"] == "ACTION":
                    hand = [Glyph.from_dict(g) for g in data["hand"]]
                    plays = FINDER.plays(hand)  # type: ignore[union-attr]
                    if plays:
                        best = max(plays, key=lambda p: sum(hand[i].value for i in p))
                        self.casts += 1
                        await socket.send(
                            json.dumps(
                                {
                                    "type": "CAST_WORD",
                                    "data": {
                                        "turn": data["turn"],
                                        "glyph_sequence": best,
                                    },
                                }
                            )
                        )
                    else:
                        self.passes += 1
                        await socket.send(
                            json.dumps(
                                {"type": "PASS_TURN", "data": {"turn": data["turn"]}}
                            )
                        )
                elif data["phase"] == "DRAFT" and data["draft_offer"]:
                    await socket.send(
                        json.dumps(
                            {
                                "type": "SELECT_PERKS",
                                "data": {
                                    "turn": data["turn"],
                                    "perk_ids": data["draft_offer"][:1],
                                },
                            }
                        )
                    )


async def play_out(a: Bot, b: Bot, match_id: str) -> None:
    await asyncio.wait_for(
        asyncio.gather(a.play(match_id), b.play(match_id)), timeout=120
    )
    assert a.ended and b.ended and a.ended["winner_id"] == b.ended["winner_id"]
    assert a.ended["winner_id"] in (a.id, b.id)

    match = (await a.http.get(f"/matchmaking/matches/{match_id}")).json()
    assert match["status"] == "FINISHED"
    assert match["winner_id"] == a.ended["winner_id"]
    assert match["total_turns"] >= 1

    casts = (await a.http.get(f"/matchmaking/matches/{match_id}/casts")).json()
    assert len(casts) == a.casts + b.casts
    for bot in (a, b):
        stats = (await bot.http.get(f"/users/{bot.id}/stats")).json()
        assert stats["matches_played"] == 1
        assert stats["rating_elo"] == 1200 + a.ended["elo_delta"][bot.id]


def names() -> tuple[str, str]:
    tag = uuid.uuid4().hex[:8]
    return f"e2e_a_{tag}", f"e2e_b_{tag}"


async def test_private_lobby_match() -> None:
    a, b = [await Bot.sign_up(n) for n in names()]
    lobby = await a.http.post(
        "/matchmaking/matches/custom",
        json={"time_control_seconds": 300},
        headers=a.csrf(),
    )
    assert lobby.status_code == 201, lobby.text
    joined = await b.http.post(
        "/matchmaking/matches/join",
        json={"invite_code": lobby.json()["invite_code"]},
        headers=b.csrf(),
    )
    assert joined.status_code == 200, joined.text

    await play_out(a, b, lobby.json()["id"])


async def test_queue_match() -> None:
    a, b = [await Bot.sign_up(n) for n in names()]
    for bot in (a, b):
        queued = await bot.http.post(
            "/matchmaking/queue", json={"time_control_seconds": 600}, headers=bot.csrf()
        )
        assert queued.status_code == 201, queued.text

    match_id = None
    for _ in range(40):  # the matchmaker worker pairs them within seconds
        status = (await a.http.get("/matchmaking/status")).json()
        if status.get("status") == "MATCHED":
            match_id = status["matched_match_id"]
            break
        await asyncio.sleep(0.5)
    assert match_id, "the matchmaker never paired the two players"

    await play_out(a, b, match_id)
    # Both can queue again once the match is over.
    again = await a.http.post(
        "/matchmaking/queue", json={"time_control_seconds": 180}, headers=a.csrf()
    )
    assert again.status_code == 201
