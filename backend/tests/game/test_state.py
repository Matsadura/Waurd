"""Core types and their JSON-safe, versioned serialization."""

import json
from typing import Any

import pytest

pytest.importorskip("backend.game", reason="The game engine is not merged yet")

from backend.game.config import Effect, GlyphType
from backend.game.state import (
    STATE_VERSION,
    EndReason,
    Glyph,
    MatchState,
    PerkInstance,
    Phase,
    PlayerState,
    Status,
)


def glyph(n: int, **changes: Any) -> Glyph:
    values: dict[str, Any] = {
        "id": f"p0-g{n}",
        "letters": "B",
        "type": GlyphType.POWER,
        "effect": Effect.DAMAGE,
        "value": 20,
        "conditional_slot": None,
    }
    return Glyph(**{**values, **changes})


def full_state() -> MatchState:
    """A state with every field set to something other than its default."""

    def player(index: int, user: str) -> PlayerState:
        return PlayerState(
            user_id=user,
            hp=73,
            defense=15,
            statuses=[Status(Effect.VULNERABLE, 2), Status(Effect.WEAK, 1)],
            draw_pile=[glyph(1), glyph(2, letters="ING", value=12)],
            hand=[
                glyph(3, type=GlyphType.SKILL, effect=Effect.HEAL, value=10),
                glyph(4, conditional_slot="end_of_word_bonus"),
            ],
            discard_pile=[glyph(5, effect=Effect.WEAK, value=2)],
            perks=[
                PerkInstance("pk-1", "amplify", 2),
                PerkInstance("pk-2", "double_or_halve", None),
            ],
            draft_offer=["ing", "erase"],
            rerolls_left=1,
            clock_ms=123_456,
            reshuffles=4,
        )

    return MatchState(
        match_id="11111111-2222-4333-8444-555555555555",
        seed="seed-123",
        time_control_seconds=180,
        players=[player(0, "user-a"), player(1, "user-b")],
        active_player=1,
        turn=7,
        phase=Phase.ENDED,
        winner=0,
        end_reason=EndReason.TIMEOUT,
    )


def roundtrip(state: MatchState) -> MatchState:
    return MatchState.from_dict(json.loads(json.dumps(state.to_dict())))


class TestSerialization:
    def test_full_state_survives_json(self) -> None:
        state = full_state()

        assert roundtrip(state) == state

    def test_default_state_survives_json(self) -> None:
        state = MatchState(
            match_id="m",
            seed="s",
            time_control_seconds=60,
            players=[
                PlayerState(user_id="a", hp=100, clock_ms=60_000, rerolls_left=3),
                PlayerState(user_id="b", hp=100, clock_ms=60_000, rerolls_left=3),
            ],
            active_player=0,
        )

        restored = roundtrip(state)

        assert restored == state
        assert restored.phase is Phase.WAITING
        assert restored.winner is None and restored.end_reason is None

    def test_document_is_plain_json(self) -> None:
        data = full_state().to_dict()

        assert data["version"] == STATE_VERSION
        assert data["phase"] == "ENDED"
        assert data["players"][0]["hand"][0]["effect"] == "HEAL"
        assert json.loads(json.dumps(data)) == data

    def test_restored_enums_are_enums(self) -> None:
        restored = roundtrip(full_state())

        assert restored.phase is Phase.ENDED
        assert restored.end_reason is EndReason.TIMEOUT
        assert restored.players[0].statuses[0].effect is Effect.VULNERABLE
        assert restored.players[0].hand[0].type is GlyphType.SKILL

    def test_restored_state_is_independent(self) -> None:
        state = full_state()
        restored = roundtrip(state)

        restored.players[0].hand.clear()

        assert len(state.players[0].hand) == 2

    @pytest.mark.parametrize("version", [None, 0, STATE_VERSION + 1, "1"])
    def test_other_versions_are_rejected(self, version: object) -> None:
        data = full_state().to_dict()
        data["version"] = version

        with pytest.raises(ValueError, match="version"):
            MatchState.from_dict(data)

    def test_missing_version_is_rejected(self) -> None:
        data = full_state().to_dict()
        del data["version"]

        with pytest.raises(ValueError, match="version"):
            MatchState.from_dict(data)

    @pytest.mark.parametrize("key", ["seed", "players", "phase"])
    def test_missing_field_is_reported(self, key: str) -> None:
        data = full_state().to_dict()
        del data[key]

        with pytest.raises(ValueError, match=f"missing '{key}'"):
            MatchState.from_dict(data)

    def test_missing_nested_field_is_reported(self) -> None:
        data = full_state().to_dict()
        del data["players"][1]["hand"][0]["letters"]

        with pytest.raises(ValueError, match="missing 'letters'"):
            MatchState.from_dict(data)


class TestMatchState:
    def test_needs_two_players(self) -> None:
        one = PlayerState(user_id="a", hp=100, clock_ms=1, rerolls_left=0)

        with pytest.raises(ValueError, match="exactly two players"):
            MatchState("m", "s", 60, players=[one], active_player=0)

    def test_active_player_is_an_index(self) -> None:
        state = full_state()

        with pytest.raises(ValueError, match="active_player"):
            MatchState("m", "s", 60, players=state.players, active_player=2)

    @pytest.mark.parametrize("index", [-1, 2])
    def test_player_lookup_checks_the_index(self, index: int) -> None:
        with pytest.raises(ValueError, match="Player index"):
            full_state().player(index)

    def test_all_glyphs(self) -> None:
        player = full_state().players[0]

        assert [g.id for g in player.all_glyphs()] == [
            "p0-g1",
            "p0-g2",
            "p0-g3",
            "p0-g4",
            "p0-g5",
        ]
