"""Play a match over the WebSocket from the terminal, as a logged-in user.

Log in (for example through /docs), copy the session_id cookie from your
browser's devtools (Storage > Cookies), then from the backend folder:

    uv run python scripts/ws_client.py <match_id> <session_id>

Commands: "cast 0 2 1" (hand positions in spelling order), "pass", "quit".
Open a second terminal with the other player's session_id to play both sides.
"""

import asyncio
import json
import sys

import websockets

SERVER = "ws://127.0.0.1:8000"
ORIGIN = "http://127.0.0.1:3000"  # must be one of CORS_ORIGINS


def show(message: dict) -> None:
    if message["type"] == "ACTION_REJECTED":
        print(f"  rejected: {message['reason']}")
        return
    if message["type"] != "STATE":
        print(f"  {message}")
        return

    you, opponent = message["you"], message["opponent"]
    hand = "  ".join(
        f"{g['position']}:{g['letter']}({g['damage']})" for g in you["hand"]
    )
    print(f"\nTurn {message['turn']}  you {you['hp']} HP  opponent {opponent['hp']} HP")
    print(f"Hand: {hand or '(not your turn yet)'}")
    if message["turn"] == 0:
        print("Waiting for the other player to connect...")
    elif message["winner"] is not None:
        print("Match over.")
    elif message["your_turn"]:
        print("Your turn: cast <positions> | pass | quit")


def to_message(line: str) -> dict | None:
    words = line.split()
    if not words:
        return None
    if words[0] == "pass":
        return {"type": "PASS_TURN"}
    if words[0] == "cast":
        return {"type": "CAST_WORD", "positions": [int(w) for w in words[1:]]}
    print("  commands: cast 0 2 1 | pass | quit")
    return None


async def main(match_id: str, session_id: str) -> None:
    url = f"{SERVER}/ws/matches/{match_id}"
    headers = {"Cookie": f"session_id={session_id}"}
    async with websockets.connect(url, origin=ORIGIN, additional_headers=headers) as ws:

        async def listen() -> None:
            async for raw in ws:
                show(json.loads(raw))

        listener = asyncio.create_task(listen())
        while True:
            line = (await asyncio.to_thread(input)).strip()
            if line == "quit":
                break
            try:
                message = to_message(line)
            except ValueError:
                print("  positions must be numbers")
                continue
            if message:
                await ws.send(json.dumps(message))
        listener.cancel()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: ws_client.py <match_id> <session_id>")
    try:
        asyncio.run(main(sys.argv[1], sys.argv[2]))
    except websockets.InvalidStatus as error:
        sys.exit(
            f"Connection refused ({error.response.status_code}): check the server logs for why."
        )
