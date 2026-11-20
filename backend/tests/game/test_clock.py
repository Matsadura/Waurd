"""Clocks, timeouts and forfeits."""

from dataclasses import replace

import pytest

pytest.importorskip("backend.game.clock", reason="Clocks are not merged yet")

from backend.game.clock import clocks, deadline_ms, remaining_ms

from backend.game.config import Effect, GlyphType
from backend.game.perks import load_catalog
from backend.game.piles import new_match
from backend.game.state import EndReason, Glyph, MatchState, Phase
from backend.game.turns import (
    Action,
    ActionType,
    EventType,
    MatchRules,
    apply,
    check_timeout,
    forfeit,
    match_state,
)

P, S = GlyphType.POWER, GlyphType.SKILL
RULES = MatchRules(frozenset({"AT", "CAB"}))
ALL_READY = {pid: replace(spec, ready=True) for pid, spec in load_catalog().items()}
DRAFTING = MatchRules(frozenset({"AT"}), catalog=ALL_READY)
USERS = ("user-a", "user-b")
MINUTE = 60_000
START = 10_000


def started(rules: MatchRules = RULES, seconds: int = 60) -> MatchState:
    state = new_match("match-1", USERS, seconds, seed="seed")
    state, _ = apply(state, Action(0, ActionType.PLAYER_READY), 1_000, rules)
    state, _ = apply(state, Action(1, ActionType.PLAYER_READY), START, rules)
    return state


def at_hand(state: MatchState) -> int:
    """Give the active player an "AT" hand; return their index."""
    active = state.active_player
    state.players[active].hand = [
        Glyph("t-a", "A", S, Effect.HEAL, 0),
        Glyph("t-t", "T", P, Effect.DAMAGE, 8),
    ]
    return active


def cast_at(state: MatchState, now_ms: int, rules: MatchRules = RULES):  # type: ignore[no-untyped-def]
    active = at_hand(state)
    return apply(
        state,
        Action(
            active, ActionType.CAST_WORD, {"turn": state.turn, "glyph_sequence": [0, 1]}
        ),
        now_ms,
        rules,
    )


class TestRunningClock:
    def test_clock_starts_when_both_are_ready(self) -> None:
        state = started()

        assert state.clock_started_ms == START
        assert deadline_ms(state) == START + MINUTE
        assert [p.clock_ms for p in state.players] == [MINUTE, MINUTE]

    def test_no_clock_before_the_start(self) -> None:
        state = new_match("match-1", USERS, 60, seed="seed")
        state, _ = apply(state, Action(0, ActionType.PLAYER_READY), 1_000, RULES)

        assert state.clock_started_ms is None
        assert deadline_ms(state) is None

    def test_only_the_active_clock_runs_and_turns_hand_it_over(self) -> None:
        state = started()
        first = state.active_player

        state, events = cast_at(state, START + 7_000)
        second = state.active_player
        state, _ = cast_at(state, START + 7_000 + 4_500)

        assert state.players[first].clock_ms == MINUTE - 7_000
        assert state.players[second].clock_ms == MINUTE - 4_500
        assert state.clock_started_ms == START + 11_500
        # Events carry the charged clocks.
        assert events[0].data["clocks"][USERS[first]] == MINUTE - 7_000

    def test_drafting_counts(self) -> None:
        state = started(DRAFTING)
        active = state.active_player
        state, _ = cast_at(state, START + 1_000, DRAFTING)
        assert state.phase == Phase.DRAFT

        state, events = apply(
            state,
            Action(active, ActionType.REROLL_PERKS, {"turn": 1}),
            START + 3_000,
            DRAFTING,
        )

        assert events[0].type == EventType.PERK_DRAFT_OPTIONS
        assert state.players[active].clock_ms == MINUTE - 3_000

    def test_rejected_action_charges_nothing_now_but_the_time_still_counts(
        self,
    ) -> None:
        state = started()
        active = state.active_player
        bad = Action(active, ActionType.CAST_WORD, {"turn": 9, "glyph_sequence": [0]})

        after, events = apply(state, bad, START + 5_000, RULES)

        assert events[0].type == EventType.ACTION_REJECTED
        assert after is state and state.players[active].clock_ms == MINUTE
        state, _ = cast_at(state, START + 8_000)
        assert state.players[active].clock_ms == MINUTE - 8_000

    def test_time_going_backwards_charges_nothing(self) -> None:
        state = started()
        active = state.active_player

        state, _ = cast_at(state, START - 5_000)

        assert state.players[active].clock_ms == MINUTE
        assert state.clock_started_ms == START


class TestTimeoutDuringAnAction:
    def test_late_action_ends_the_match_instead(self) -> None:
        state = started()
        active = state.active_player
        other_hp = state.players[1 - active].hp

        state, events = cast_at(state, START + MINUTE)

        [ended] = events
        assert ended.type == EventType.MATCH_ENDED
        assert ended.to == (0, 1)
        assert ended.data["end_reason"] == "TIMEOUT"
        assert ended.data["winner_id"] == USERS[1 - active]
        assert ended.data["clocks"][USERS[active]] == 0
        assert (state.phase, state.winner, state.end_reason) == (
            Phase.ENDED,
            1 - active,
            EndReason.TIMEOUT,
        )
        # The word was never cast.
        assert state.players[1 - active].hp == other_hp
        assert state.clock_started_ms is None

    def test_one_millisecond_left_is_still_in_time(self) -> None:
        state = started()

        state, events = cast_at(state, START + MINUTE - 1)

        assert events[0].type == EventType.WORD_RESOLVED

    def test_any_message_after_the_deadline_ends_it(self) -> None:
        state = started()
        waiting = 1 - state.active_player

        state, events = apply(
            state,
            Action(waiting, ActionType.REROLL_PERKS, {"turn": 1}),
            START + MINUTE + 5,
            RULES,
        )

        assert events[0].data["end_reason"] == "TIMEOUT"
        assert events[0].data["winner_id"] == USERS[waiting]


class TestCheckTimeout:
    def test_before_the_deadline_nothing_changes(self) -> None:
        state = started()

        after, events = check_timeout(state, START + MINUTE - 1)

        assert after is state and events == []
        assert state.clock_started_ms == START

    def test_at_the_deadline_the_active_player_loses(self) -> None:
        state = started()
        active = state.active_player
        before = state.to_dict()

        after, [ended] = check_timeout(state, START + MINUTE)

        assert ended.data["end_reason"] == "TIMEOUT"
        assert after.winner == 1 - active
        assert state.to_dict() == before

    def test_no_clock_no_timeout(self) -> None:
        waiting = new_match("match-1", USERS, 60, seed="seed")
        assert check_timeout(waiting, 10**12) == (waiting, [])

        ended, _ = forfeit(started(), 0, EndReason.RESIGNATION, START)
        assert check_timeout(ended, 10**12) == (ended, [])

    def test_deadline_follows_the_turns(self) -> None:
        state = started()
        state, _ = cast_at(state, START + 20_000)

        assert deadline_ms(state) == START + 20_000 + MINUTE


class TestForfeit:
    @pytest.mark.parametrize("reason", [EndReason.RESIGNATION, EndReason.DISCONNECT])
    def test_the_other_player_wins(self, reason: EndReason) -> None:
        state = started()
        before = state.to_dict()

        after, [ended] = forfeit(state, 1, reason, START + 1_000)

        assert ended.to == (0, 1)
        assert ended.data["winner_id"] == USERS[0]
        assert ended.data["end_reason"] == reason.value
        assert (after.phase, after.winner, after.end_reason) == (Phase.ENDED, 0, reason)
        assert state.to_dict() == before

    def test_the_waiting_player_can_resign_too(self) -> None:
        state = started()
        waiting = 1 - state.active_player

        after, _ = forfeit(state, waiting, EndReason.RESIGNATION, START)

        assert after.winner == state.active_player

    def test_before_the_start(self) -> None:
        state = new_match("match-1", USERS, 60, seed="seed")

        after, [ended] = forfeit(state, 0, EndReason.DISCONNECT, 0)

        assert ended.data["winner_id"] == USERS[1]
        assert after.phase == Phase.ENDED

    def test_charges_the_active_clock(self) -> None:
        state = started()
        active = state.active_player

        after, events = forfeit(state, 1 - active, EndReason.RESIGNATION, START + 2_500)

        assert after.players[active].clock_ms == MINUTE - 2_500
        assert events[0].data["clocks"][USERS[active]] == MINUTE - 2_500

    def test_a_clock_already_at_zero_is_a_timeout(self) -> None:
        state = started()
        active = state.active_player

        after, [ended] = forfeit(
            state, 1 - active, EndReason.RESIGNATION, START + MINUTE
        )

        assert ended.data["end_reason"] == "TIMEOUT"
        assert after.winner == 1 - active

    def test_after_the_end_nothing_happens(self) -> None:
        state, _ = forfeit(started(), 0, EndReason.RESIGNATION, START)

        after, events = forfeit(state, 1, EndReason.RESIGNATION, START)

        assert after is state and events == []
        assert state.winner == 1

    @pytest.mark.parametrize("reason", [EndReason.TIMEOUT, EndReason.HEALTH_DEPLETED])
    def test_only_resignation_or_disconnect(self, reason: EndReason) -> None:
        with pytest.raises(ValueError):
            forfeit(started(), 0, reason, START)

    def test_player_index_is_checked(self) -> None:
        with pytest.raises(ValueError):
            forfeit(started(), 2, EndReason.RESIGNATION, START)

    def test_open_draft_is_closed(self) -> None:
        state = started(DRAFTING)
        active = state.active_player
        state, _ = cast_at(state, START, DRAFTING)
        assert state.players[active].draft_offer

        after, _ = forfeit(state, active, EndReason.RESIGNATION, START)

        assert after.players[active].draft_offer == []
        assert deadline_ms(after) is None


class TestSnapshotClocks:
    def test_live_clock_for_the_active_player_only(self) -> None:
        state = started()
        active = state.active_player

        data = match_state(state, 1 - active, START + 12_000).data

        assert data["clocks"] == {
            USERS[active]: MINUTE - 12_000,
            USERS[1 - active]: MINUTE,
        }
        assert data["clock_running_for"] == USERS[active]
        assert state.players[active].clock_ms == MINUTE

    def test_without_now_shows_the_last_charge(self) -> None:
        state = started()

        assert match_state(state, 0).data["clocks"] == {u: MINUTE for u in USERS}

    def test_never_below_zero(self) -> None:
        state = started()

        assert remaining_ms(state, state.active_player, START + 10 * MINUTE) == 0
        assert min(clocks(state, START + 10 * MINUTE).values()) == 0

    def test_no_clock_running_after_the_end(self) -> None:
        state, _ = forfeit(started(), 0, EndReason.RESIGNATION, START)

        data = match_state(state, 0, START + 99_000).data

        assert data["clock_running_for"] is None
        assert data["clocks"] == {u: MINUTE for u in USERS}
