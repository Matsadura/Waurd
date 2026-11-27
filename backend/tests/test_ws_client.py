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
        {
            "position": i,
            "letter": letter,
            "type": "power",
            "effect_type": "damage",
            "effect_value": value,
        }
        for i, (letter, value) in enumerate(glyphs)
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
        "log": ["alice goes first"],
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
    def test_a_cast_word_is_sent_and_the_server_log_shown(self) -> None:
        game = ws_client.Game(me="alice", opponent="bob")
        game.on_message(state())

        assert game.command("cat") == {"type": "CAST_WORD", "positions": [0, 1, 2]}
        game.on_message(
            state(
                turn=2,
                your_turn=False,
                you={"hp": 100, "hand": []},
                opponent={"hp": 74, "hand_size": 12},
                log=["alice goes first", "alice cast CAT for 26 damage"],
            )
        )

        assert len(game.log) == 2  # each server line shown once
        assert "alice cast CAT for 26 damage" in game.log[-1]

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


class TestPerks:
    def game(self, **you):  # type: ignore[no-untyped-def]
        game = ws_client.Game(me="alice", opponent="bob")
        base = state()
        base["you"] = {**base["you"], **you}
        game.on_message(base)
        return game

    def test_use_sends_the_perk_instance_and_slot(self) -> None:
        game = self.game(
            perks=[{"instance_id": 7, "name": "Sharpen", "durability_left": 4}]
        )

        assert game.command("/use 1 2") == {
            "type": "APPLY_PERK",
            "perk_instance_id": 7,
            "position": 2,
        }

    def test_pick_sends_the_offered_perk(self) -> None:
        draft = {
            "options": [{"perk_id": "hex", "name": "Hex", "rarity": "uncommon"}],
            "rerolls_left": 3,
        }
        game = self.game(perks=[], draft=draft)

        assert game.command("/pick 1") == {"type": "SELECT_PERKS", "perk_ids": ["hex"]}
        assert game.command("/skip") == {"type": "SELECT_PERKS", "perk_ids": []}
        assert game.command("/reroll") == {"type": "REROLL_PERKS"}

    def test_bad_numbers_are_not_sent(self) -> None:
        game = self.game(perks=[], draft=None)

        assert game.command("/pick 3") is None
        assert game.command("/use 1 0") is None
        assert "like: /use 1 4" in game.note

    def test_the_screen_shows_perks_and_the_draft(self) -> None:
        draft = {
            "options": [{"perk_id": "hex", "name": "Hex", "rarity": "uncommon"}],
            "rerolls_left": 2,
        }
        game = self.game(
            perks=[{"instance_id": 1, "name": "Sharpen", "durability_left": 3}],
            draft=draft,
        )

        screen = "\n".join(game.render())

        assert "1) Sharpen x3" in screen
        assert "1) Hex (uncommon)" in screen and "(2 left)" in screen
