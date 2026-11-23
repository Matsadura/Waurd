"""The terminal client (scripts/ws_client.py): spelling words and reading turns."""

import sys
from pathlib import Path

import pytest

import backend

# scripts/ sits next to src/, which holds the backend package
sys.path.insert(0, str(Path(backend.__file__).parents[2] / "scripts"))
ws_client = pytest.importorskip(
    "ws_client", reason="The terminal client is not merged yet"
)


def hand(*glyphs: tuple[str, int]) -> list[dict]:
    return [
        {"position": i, "letter": letter, "damage": damage}
        for i, (letter, damage) in enumerate(glyphs)
    ]


def state(**changes):  # type: ignore[no-untyped-def]
    base = {
        "type": "STATE",
        "turn": 1,
        "your_turn": True,
        "winner": None,
        "you_won": None,
        "end_reason": None,
        "you": {"hp": 100, "hand": hand(("C", 12), ("A", 6), ("T", 8))},
        "opponent": {"hp": 100, "hand_size": 0},
        "time_left": {"you": 90, "opponent": 90},
    }
    return {**base, **changes}


class TestSpelling:
    def test_a_word_uses_the_strongest_copy_of_each_letter(self) -> None:
        glyphs = hand(("C", 12), ("A", 6), ("T", 8), ("A", 9))

        assert ws_client.positions_for("cat", glyphs) == [0, 3, 2]
        assert ws_client.positions_for("caat", glyphs) == [0, 3, 1, 2]

    def test_missing_letters_give_nothing(self) -> None:
        assert ws_client.positions_for("dog", hand(("C", 12))) is None


class TestTurns:
    def test_a_cast_word_is_sent_and_its_damage_reported(self) -> None:
        game = ws_client.Game(me="alice", opponent="bob")
        game.on_message(state())

        assert game.command("cat") == {"type": "CAST_WORD", "positions": [0, 1, 2]}
        game.on_message(
            state(
                turn=2,
                your_turn=False,
                you={"hp": 100, "hand": []},
                opponent={"hp": 74, "hand_size": 12},
            )
        )

        assert "You cast CAT for 26 damage" in game.log[-1]

    def test_resigning_needs_confirmation(self) -> None:
        game = ws_client.Game(me="alice", opponent="bob")
        game.on_message(state())

        assert game.command("/resign") is None
        assert game.command("/resign") == {"type": "RESIGN"}

    def test_the_result_names_the_reason(self) -> None:
        game = ws_client.Game(me="alice", opponent="bob")
        game.on_message(state())
        game.on_message(state(winner=0, you_won=True, end_reason="TIMEOUT"))

        assert game.over
        assert "bob ran out of time" in game.banner
