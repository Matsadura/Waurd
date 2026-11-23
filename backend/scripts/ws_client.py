"""Play Waurd live in the terminal.

From the backend folder:

    uv run python scripts/ws_client.py

Log in (or create an account), then pick a quick match, host a private match,
or join one with an invite code. To play both sides, run it again in a second
terminal as another user.

In a match, type a word to cast it with letters from your hand. Hand positions
in spelling order ("0 4 2") work too. Commands: /pass /resign /help /quit.
If the connection drops, the client reconnects by itself. If you quit, run it
again within 30 seconds to get back into the match.

Options: --server (default http://localhost:8000), --origin (must be one of the
backend's CORS_ORIGINS, default http://localhost:5173), --email, --password.
"""

import argparse
import asyncio
import getpass
import itertools
import json
import math
import os
import sys
import threading
import time
from dataclasses import dataclass, field

import httpx
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatus

from backend.game.rules import STARTING_HP

API = "/api/v1"
TIME_CONTROLS = {"1": 180, "2": 300, "3": 600}
WIDTH = 74
LOG_LINES = 5
LIVE_ROWS = (2, 3, 5)  # the rows with running clocks, redrawn every half second

COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ
BOLD, DIM, INVERT = "1", "2", "7"
RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN = "31", "32", "33", "34", "35", "36"

REASONS = {  # end_reason: (said to the winner, said to the loser)
    "HEALTH_DEPLETED": ("{opponent} ran out of HP", "you ran out of HP"),
    "RESIGNATION": ("{opponent} resigned", "you resigned"),
    "DISCONNECT": ("{opponent} left the match", "you were away too long"),
    "TIMEOUT": ("{opponent} ran out of time", "you ran out of time"),
}


class Quit(Exception):
    """The input was closed (Ctrl+D)."""


def paint(text: str, *styles: str) -> str:
    styles = tuple(style for style in styles if style)
    if not COLOR or not styles:
        return text
    return f"\033[{';'.join(styles)}m{text}\033[0m"


def write(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def bar(value: float, total: float, width: int, color: str) -> str:
    filled = round(width * max(0.0, min(value, total)) / total)
    return paint("█" * filled, color) + paint("░" * (width - filled), DIM)


def clock(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    whole = math.ceil(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


# --- Account and matchmaking, over HTTP --------------------------------------


def detail(response: httpx.Response) -> str:
    """The server's error message, readable."""
    try:
        message = response.json().get("detail", response.text)
    except (ValueError, AttributeError):
        return f"HTTP {response.status_code}"
    if isinstance(message, list):  # validation errors
        return "; ".join(item.get("msg", str(item)) for item in message)
    return str(message)


def csrf(http: httpx.Client) -> dict:
    return {"X-CSRF-Token": http.cookies.get("csrf_token", "")}


def yes(question: str) -> bool:
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def log_in(http: httpx.Client, email: str | None, password: str | None) -> dict:
    """Log in, offering to create the account if it doesn't exist."""
    while True:
        email = email or input("Email: ").strip()
        password = password or getpass.getpass("Password: ")
        response = http.post(
            f"{API}/auth/login", json={"email": email, "password": password}
        )
        if response.status_code == 202:  # two-factor: a code was emailed
            code = input(f"Code sent to {response.json()['email_hint']}: ").strip()
            response = http.post(f"{API}/auth/2fa/verify", json={"code": code})
        if response.status_code == 200:
            return response.json()

        print(paint(detail(response), RED))
        if response.status_code == 401 and yes(f"Create an account for {email}?"):
            username = input("Username: ").strip()
            created = http.post(
                f"{API}/auth/register",
                json={"username": username, "email": email, "password": password},
            )
            if created.status_code in (200, 201):
                continue  # now log in with it
            print(paint(detail(created), RED))
        email = password = None


def read_lines(loop: asyncio.AbstractEventLoop) -> asyncio.Queue:
    """Typed lines, one per item; None when the input closes."""
    lines: asyncio.Queue = asyncio.Queue()

    def read() -> None:
        for line in sys.stdin:
            loop.call_soon_threadsafe(lines.put_nowait, line.rstrip("\n"))
        loop.call_soon_threadsafe(lines.put_nowait, None)

    threading.Thread(target=read, daemon=True).start()
    return lines


async def ask(lines: asyncio.Queue, prompt: str) -> str:
    write(prompt)
    line = await lines.get()
    if line is None:
        raise Quit
    return line.strip()


async def wait_until_matched(http, lines, text: str, cancel) -> str | None:
    """Poll the matchmaking status until there is a match; Enter cancels."""
    spinner = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
    while True:
        response = http.get(f"{API}/matchmaking/status")
        if response.status_code == 404:
            print(paint("\nNot waiting for a match anymore.", YELLOW))
            return None
        if response.json()["status"] == "MATCHED":
            print()
            return response.json()["matched_match_id"]
        write(f"\r{paint(next(spinner), CYAN)} {text}  {paint('Enter cancels', DIM)} ")
        try:
            await asyncio.wait_for(lines.get(), 1)
        except TimeoutError:
            continue
        cancel()
        print("Cancelled.")
        return None


async def find_match(
    http: httpx.Client, lines: asyncio.Queue
) -> tuple[str | None, bool]:
    """Get the player into a match: its id (None to quit), and if it's a rejoin."""
    response = http.get(f"{API}/matchmaking/status")
    if response.status_code == 200:  # already queued, hosting, or playing
        ticket = response.json()
        if ticket["status"] == "MATCHED":
            print(paint("You're already in a match: rejoining.", YELLOW))
            return ticket["matched_match_id"], True
        if ticket["status"] == "WAITING":
            return await host(http, lines, ticket["matched_match_id"]), False
        seconds = ticket["time_control_seconds"]
        return await queue(http, lines, seconds, joined=True), False

    while True:
        print(f"\n  {paint('1', BOLD, CYAN)}  Quick match")
        print(f"  {paint('2', BOLD, CYAN)}  Host a private match")
        print(f"  {paint('3', BOLD, CYAN)}  Join with an invite code")
        print(f"  {paint('q', BOLD, CYAN)}  Quit")
        choice = (await ask(lines, "> ")).lower()
        if choice == "q":
            return None, False
        if choice == "3":
            code = await ask(lines, "Invite code: ")
            joined = http.post(
                f"{API}/matchmaking/matches/join",
                json={"invite_code": code},
                headers=csrf(http),
            )
            if joined.status_code == 200:
                return joined.json()["id"], False
            print(paint(detail(joined), RED))
            continue
        if choice not in ("1", "2"):
            continue

        minutes = await ask(lines, "Time: 1) 3 min  2) 5 min  3) 10 min  [2] ")
        seconds = TIME_CONTROLS.get(minutes or "2", 300)
        match_id = (
            await queue(http, lines, seconds)
            if choice == "1"
            else await host(http, lines, None, seconds)
        )
        if match_id:
            return match_id, False


async def queue(http, lines, seconds: int, joined: bool = False) -> str | None:
    body = {"time_control_seconds": seconds}
    if not joined:
        response = http.post(f"{API}/matchmaking/queue", json=body, headers=csrf(http))
        if response.status_code != 201:
            print(paint(detail(response), RED))
            return None

    def leave() -> None:
        http.request(
            "DELETE", f"{API}/matchmaking/queue", json=body, headers=csrf(http)
        )

    text = f"Looking for an opponent ({seconds // 60} min)"
    return await wait_until_matched(http, lines, text, leave)


async def host(http, lines, match_id: str | None, seconds: int = 300) -> str | None:
    if match_id is None:
        response = http.post(
            f"{API}/matchmaking/matches/custom",
            json={"time_control_seconds": seconds},
            headers=csrf(http),
        )
        if response.status_code != 201:
            print(paint(detail(response), RED))
            return None
        match_id, code = response.json()["id"], response.json()["invite_code"]
    else:  # a lobby this player already opened
        code = http.get(f"{API}/matchmaking/matches/{match_id}").json()["invite_code"]

    print(f"\n  Invite code: {paint(f' {code} ', BOLD, INVERT, YELLOW)}\n")

    def cancel() -> None:
        http.delete(f"{API}/matchmaking/matches/{match_id}", headers=csrf(http))

    return await wait_until_matched(http, lines, "Waiting for your friend", cancel)


def opponent_of(http: httpx.Client, match_id: str, my_id: str) -> str:
    response = http.get(f"{API}/matchmaking/matches/{match_id}")
    if response.status_code == 200:
        for seat in ("player1", "player2"):
            player = response.json().get(seat)
            if player and player["id"] != my_id:
                return player["username"]
    return "opponent"


# --- The match ---------------------------------------------------------------


def positions_for(word: str, hand: list[dict]) -> list[int] | None:
    """Hand positions spelling the word, strongest glyph first for repeated letters."""
    strongest_first = sorted(hand, key=lambda glyph: -glyph["damage"])
    picked: list[int] = []
    for letter in word.upper():
        glyph = next(
            (
                g
                for g in strongest_first
                if g["letter"] == letter and g["position"] not in picked
            ),
            None,
        )
        if glyph is None:
            return None
        picked.append(glyph["position"])
    return picked


@dataclass
class Game:
    me: str
    opponent: str
    state: dict | None = None
    received_at: float = 0.0
    log: list[str] = field(default_factory=list)
    note: str = ""
    banner: str = ""
    pending: str | None = None  # the word just cast, until the server answers
    away_until: float | None = None  # when the disconnected opponent forfeits
    confirm_resign: bool = False
    rejoining: bool = False  # back into a match that was already being played
    over: bool = False
    quit: bool = False

    # Messages from the server

    def on_message(self, message: dict) -> None:
        kind = message["type"]
        if kind == "STATE":
            self.on_state(message)
        elif kind == "ACTION_REJECTED":
            self.note, self.pending = message["reason"], None
        elif kind == "OPPONENT_DISCONNECTED":
            self.away_until = time.monotonic() + message["grace_seconds"]
            self.say(f"{self.opponent} disconnected", YELLOW)
        elif kind == "OPPONENT_RECONNECTED":
            self.away_until = None
            self.say(f"{self.opponent} is back", YELLOW)
        elif kind == "MATCH_ABORTED":
            self.over = True
            self.banner = paint(" ABORTED ", BOLD, INVERT, YELLOW) + (
                f"  {self.opponent} never arrived. No rating change."
            )

    def on_state(self, state: dict) -> None:
        before, self.state, self.received_at = self.state, state, time.monotonic()
        started = state["turn"] > 0 and (before is None or before["turn"] == 0)
        if started and state["turn"] == 1 and not self.rejoining:
            first = "You go" if state["your_turn"] else f"{self.opponent} goes"
            self.say(f"The match has started. {first} first.", BOLD)
        elif started:
            self.say("Back in the match.", BOLD)
        elif before and (
            state["turn"] != before["turn"] or state["winner"] is not None
        ):
            self.describe_turn(before, state)
            self.note = ""

        if state["winner"] is not None:
            self.over = True
            win, lose = REASONS.get(state["end_reason"], ("", ""))
            if state["you_won"]:
                self.banner = (
                    paint(" VICTORY ", BOLD, INVERT, GREEN)
                    + "  "
                    + (win.format(opponent=self.opponent))
                )
            else:
                self.banner = paint(" DEFEAT ", BOLD, INVERT, RED) + "  " + lose

    def describe_turn(self, before: dict, after: dict) -> None:
        if before["your_turn"]:
            dealt = before["opponent"]["hp"] - after["opponent"]["hp"]
            if dealt > 0:
                self.say(
                    f"You cast {self.pending or 'a word'} for {dealt} damage", GREEN
                )
            elif self.pending == "/pass":
                self.say("You passed")
            elif after["winner"] is None:
                self.say("Your turn ran out", YELLOW)
        else:
            taken = before["you"]["hp"] - after["you"]["hp"]
            if taken > 0:
                self.say(f"{self.opponent} hit you for {taken}", RED)
            elif after["winner"] is None:
                self.say(f"{self.opponent} passed")
        self.pending = None

    def say(self, text: str, style: str = "") -> None:
        self.log = [*self.log, paint(" · ", DIM) + paint(text, style)][-LOG_LINES:]

    # What the player typed

    def command(self, line: str) -> dict | None:
        """The message to send for a typed line, if any."""
        if self.over:
            self.quit = True  # Enter on the result screen
            return None
        line, self.note = line.strip(), ""
        resigning, self.confirm_resign = self.confirm_resign, False
        if not line:
            return None
        if line.startswith("/"):
            name = line[1:].lower()
            if name in ("q", "quit"):
                self.quit = True
            elif name in ("p", "pass"):
                self.pending = "/pass"
                return {"type": "PASS_TURN"}
            elif name in ("r", "resign"):
                if resigning:
                    return {"type": "RESIGN"}
                self.confirm_resign = True
                self.note = "Type /resign again to give up the match."
            elif name in ("h", "help"):
                self.say("Type a word to cast it with your glyphs, like: cat")
                self.say("Or type hand positions in spelling order, like: 0 4 2")
                self.say("/pass ends your turn, /resign gives up the match")
                self.say("/quit leaves; run the client again within 30s to come back")
            else:
                self.note = f"Unknown command {line}. Type /help."
            return None

        hand = self.state["you"]["hand"] if self.state else []
        if not hand:
            self.note = "Wait for your turn: your glyphs are drawn when it starts."
            return None
        parts = line.split()
        if all(part.isdigit() for part in parts):
            positions = [int(part) for part in parts]
            self.pending = "".join(
                hand[p]["letter"] for p in positions if p < len(hand)
            )
            return {"type": "CAST_WORD", "positions": positions}
        if not line.isalpha():
            self.note = "Type a word (letters only), or positions like 0 4 2."
            return None
        positions = positions_for(line, hand)
        if positions is None:
            self.note = f"You don't have the letters for {line.upper()}."
            return None
        self.pending = line.upper()
        return {"type": "CAST_WORD", "positions": positions}

    # Drawing

    def running(self) -> bool:
        s = self.state
        return bool(s and s["turn"] > 0 and s["winner"] is None and not self.over)

    def time_left(self, mine: bool) -> float | None:
        if "time_left" not in self.state:  # the saved result after the end has none
            return None
        seconds = self.state["time_left"]["you" if mine else "opponent"]
        if self.running() and self.state["your_turn"] == mine:
            seconds -= time.monotonic() - self.received_at
        return max(0.0, seconds)

    def render(self) -> list[str]:
        rule = paint("─" * WIDTH, DIM)
        if self.state is None:
            return [self.title(), rule, "", "", rule, paint(" Connecting…", DIM)]
        log = self.log + [""] * (LOG_LINES - len(self.log))
        note = paint(f" ! {self.note}", RED) if self.note else ""
        hint = (
            " Press Enter to continue."
            if self.over
            else " Type a word to cast it · positions like 0 4 2 · /pass /resign /help /quit"
        )
        return [
            self.title(),
            rule,
            self.player_row(mine=True),
            self.player_row(mine=False),
            rule,
            self.status(),
            "",
            *self.hand(),
            "",
            *log,
            "",
            note,
            paint(hint, DIM),
        ]

    def title(self) -> str:
        left = paint(" WAURD ", BOLD, INVERT, MAGENTA) + (
            f"  {paint(self.me, BOLD)} vs {paint(self.opponent, BOLD)}"
        )
        turn = f"turn {self.state['turn']}" if self.state and self.state["turn"] else ""
        used = 9 + len(self.me) + 4 + len(self.opponent)
        return left + " " * max(1, WIDTH - used - len(turn)) + paint(turn, DIM)

    def player_row(self, mine: bool) -> str:
        hp = self.state["you" if mine else "opponent"]["hp"]
        active = self.running() and self.state["your_turn"] == mine
        seconds = self.time_left(mine)
        name = (self.me if mine else self.opponent)[:14]
        hp_color = GREEN if hp > 50 else YELLOW if hp > 25 else RED
        low = seconds is not None and seconds < 30
        clock_style = (BOLD, RED if low else "") if active else (DIM,)
        return (
            f" {paint('▶', BOLD, YELLOW) if active else ' '} "
            f"{paint(f'{name:<14}', BOLD if mine else '')}  "
            f"{bar(hp, STARTING_HP, 20, hp_color)} {hp:>3} HP   "
            f"{paint('⏱ ' + clock(seconds), *clock_style)}"
        )

    def status(self) -> str:
        s = self.state
        if self.over:
            return " " + self.banner
        if s["turn"] == 0:
            return paint(f" Waiting for {self.opponent} to connect…", YELLOW)
        if self.away_until is not None:
            left = max(0, int(self.away_until - time.monotonic()))
            return paint(
                f" {self.opponent} disconnected: they lose in {left}s unless they return",
                YELLOW,
            )
        if s["your_turn"]:
            return " " + paint(" YOUR TURN ", BOLD, INVERT, GREEN)
        return " " + paint(f" {self.opponent.upper()}'S TURN ", BOLD, INVERT, BLUE)

    def hand(self) -> list[str]:
        glyphs = self.state["you"]["hand"]
        if not glyphs:
            waiting = self.running() and not self.state["your_turn"]
            text = "Your glyphs are drawn when your turn starts." if waiting else ""
            return ["", paint(f"   {text}", DIM), "", "", ""]
        rows = ["  "] * 5
        for g in glyphs:
            color = (
                MAGENTA if g["damage"] >= 15 else YELLOW if g["damage"] >= 10 else CYAN
            )
            rows[0] += paint("┌───┐", color) + " "
            rows[1] += (
                paint("│", color)
                + paint(f" {g['letter']} ", BOLD)
                + paint("│", color)
                + " "
            )
            rows[2] += paint(f"│{g['damage']:>3}│", color) + " "
            rows[3] += paint("└───┘", color) + " "
            rows[4] += paint(f"{g['position']:^5}", DIM) + " "
        return rows


def draw(game: Game) -> None:
    prompt = "" if game.over else paint("> ", BOLD, GREEN)
    write("\033[H\033[2J" + "\n".join(game.render()) + "\n" + prompt)


def draw_clocks(game: Game) -> None:
    """Redraw only the clock rows, leaving the cursor (and the typing) alone."""
    if not game.running():
        return
    rows = game.render()
    write(
        "\0337"
        + "".join(f"\033[{row + 1};1H\033[2K{rows[row]}" for row in LIVE_ROWS)
        + "\0338"
    )


async def connected(ws, game: Game, lines: asyncio.Queue) -> None:
    """Play over one connection, until it closes or the player is done."""

    async def receive() -> None:
        async for raw in ws:
            game.on_message(json.loads(raw))
            draw(game)

    async def send() -> None:
        while not game.quit:
            line = await lines.get()
            if line is None:
                raise Quit
            message = game.command(line)
            if message:
                await ws.send(json.dumps(message))
            if not game.quit:
                draw(game)

    async def tick() -> None:
        while True:
            await asyncio.sleep(0.5)
            draw_clocks(game)

    tasks = [asyncio.create_task(job()) for job in (receive, send, tick)]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        task.result()  # raise what ended it, if it was an error


async def play(args, http, user: dict, match_id: str, lines, rejoining: bool) -> Game:
    opponent = opponent_of(http, match_id, user["id"])
    game = Game(me=user["username"], opponent=opponent, rejoining=rejoining)
    url = f"{args.server.replace('http', 'ws', 1)}/ws/matches/{match_id}"
    headers = {"Cookie": f"session_id={http.cookies.get('session_id', '')}"}
    failures = 0
    draw(game)
    while not (game.over or game.quit):
        try:
            async with websockets.connect(
                url, origin=args.origin, additional_headers=headers
            ) as ws:
                if failures:
                    game.say("Reconnected.", GREEN)
                failures, game.note = 0, ""
                await connected(ws, game, lines)
        except InvalidStatus as error:
            if game.state is None:
                raise SystemExit(
                    f"\nThe server refused the connection (HTTP {error.response.status_code})."
                    f" Check that --origin {args.origin} is in the backend's CORS_ORIGINS."
                ) from None
            game.over = True  # refused on a reconnect: the match no longer exists
            game.banner = paint(" GONE ", BOLD, INVERT, YELLOW) + (
                "  This match no longer exists (the server may have restarted)."
            )
        except (OSError, ConnectionClosed):
            pass
        if game.over or game.quit:
            break
        failures += 1
        if failures > 10:
            raise SystemExit("\nLost the connection to the server.")
        game.note = f"Connection lost, reconnecting (try {failures})…"
        draw(game)
        await asyncio.sleep(2)

    if game.over and not game.quit:  # show the result until Enter
        draw(game)
        await ask(lines, "")
    return game


async def run(args, http: httpx.Client, user: dict) -> None:
    lines = read_lines(asyncio.get_running_loop())
    print(f"Hi {paint(user['username'], BOLD)}!")
    try:
        while True:
            match_id, rejoining = await find_match(http, lines)
            if match_id is None:
                return
            game = await play(args, http, user, match_id, lines, rejoining)
            if game.quit and not game.over:
                print(
                    "\nYou left the match. Run the client again within 30 seconds"
                    " to come back, or you lose."
                )
                return
            if (await ask(lines, "\nPlay again? [y/N] ")).lower() not in ("y", "yes"):
                return
    except Quit:
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Play Waurd in the terminal.")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--origin", default="http://localhost:5173")
    parser.add_argument("--email")
    parser.add_argument("--password")
    args = parser.parse_args()

    http = httpx.Client(base_url=args.server, timeout=10)
    try:
        user = log_in(http, args.email, args.password)
        asyncio.run(run(args, http, user))
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")
    except httpx.HTTPError:
        sys.exit(f"\nCan't reach the server at {args.server}. Is the backend running?")


if __name__ == "__main__":
    main()
