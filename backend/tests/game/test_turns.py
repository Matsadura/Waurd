"""The turn state machine: apply(state, action, now_ms, rules) -> (state, events)."""

import json
from dataclasses import replace

import pytest

pytest.importorskip(
    "backend.game.turns", reason="The turn state machine is not merged yet"
)

from backend.game.config import Effect, GameConfig, GlyphType
from backend.game.perks import grant_perk, load_catalog
from backend.game.piles import new_match
from backend.game.state import EndReason, Glyph, MatchState, Phase, Status
from backend.game.turns import (
    Action,
    ActionType,
    EventType,
    MatchRules,
    Rejection,
    apply,
    match_state,
    parse_action,
)

P, S = GlyphType.POWER, GlyphType.SKILL
WORDS = frozenset({"CAB", "BAT", "TAB", "EVE", "AT", "TA", "SAT", "TATS"})
RULES = MatchRules(WORDS)
ALL_READY = {pid: replace(spec, ready=True) for pid, spec in load_catalog().items()}
DRAFTING = MatchRules(WORDS, catalog=ALL_READY)
USERS = ("user-a", "user-b")


def g(
    n: int,
    letters: str,
    type_: GlyphType = P,
    effect: Effect = Effect.DAMAGE,
    value: int = 8,
) -> Glyph:
    return Glyph(f"t-{n}", letters, type_, effect, value)


def act(
    state: MatchState, player: int, type_: ActionType, rules: MatchRules = RULES, **data
):  # type: ignore[no-untyped-def]
    return apply(state, Action(player, type_, data), 0, rules)


def started(seed: str = "seed", rules: MatchRules = RULES) -> MatchState:
    state = new_match("match-1", USERS, 180, seed=seed)
    state, _ = act(state, 0, ActionType.PLAYER_READY, rules)
    state, _ = act(state, 1, ActionType.PLAYER_READY, rules)
    return state


def with_hand(state: MatchState, *glyphs: Glyph) -> int:
    """Give the active player this hand; returns the active player's index."""
    active = state.active_player
    state.players[active].hand = list(glyphs)
    return active


def cab() -> tuple[Glyph, ...]:
    return (g(0, "C", value=12), g(1, "A", S, Effect.HEAL, 10), g(2, "B", value=20))


def types(events) -> list[str]:  # type: ignore[no-untyped-def]
    return [e.type.value for e in events]


def rejected(events, code: str) -> None:  # type: ignore[no-untyped-def]
    [event] = events
    assert event.type == EventType.ACTION_REJECTED
    assert event.data["code"] == code


class TestStart:
    def test_one_ready_player_waits(self) -> None:
        state = new_match("match-1", USERS, 180, seed="seed")

        state, events = act(state, 0, ActionType.PLAYER_READY)

        assert events == []
        assert state.phase == Phase.WAITING
        assert state.players[0].ready is True

    def test_both_ready_starts_turn_one(self) -> None:
        state = new_match("match-1", USERS, 180, seed="seed")
        state, _ = act(state, 1, ActionType.PLAYER_READY)

        state, events = act(state, 0, ActionType.PLAYER_READY)

        active = state.active_player
        assert (state.turn, state.phase) == (1, Phase.ACTION)
        assert types(events) == ["MATCH_START", "TURN_START", "OPPONENT_TURN_START"]
        start, mine, theirs = events
        assert start.to == (0, 1)
        assert start.data["first_player_id"] == USERS[active]
        assert start.data["players"] == [{"id": u, "hp": 100} for u in USERS]
        assert mine.to == (active,)
        assert len(mine.data["hand_glyphs"]) == 7
        assert theirs.to == (1 - active,)
        assert theirs.data["hand_size"] == 7
        assert "hand_glyphs" not in theirs.data
        assert len(state.players[active].hand) == 7
        assert state.players[1 - active].hand == []

    def test_ready_twice_is_rejected(self) -> None:
        state = new_match("match-1", USERS, 180, seed="seed")
        state, _ = act(state, 0, ActionType.PLAYER_READY)

        _, events = act(state, 0, ActionType.PLAYER_READY)

        rejected(events, Rejection.ALREADY_READY)

    def test_ready_after_start_is_rejected(self) -> None:
        _, events = act(started(), 0, ActionType.PLAYER_READY)
        rejected(events, Rejection.WRONG_PHASE)

    def test_cannot_cast_before_the_match_starts(self) -> None:
        state = new_match("match-1", USERS, 180, seed="seed")

        _, events = act(
            state, state.active_player, ActionType.CAST_WORD, turn=0, glyph_sequence=[0]
        )

        rejected(events, Rejection.WRONG_PHASE)


class TestRejections:
    def test_not_your_turn(self) -> None:
        state = started()
        waiting = 1 - state.active_player

        _, events = act(
            state, waiting, ActionType.CAST_WORD, turn=1, glyph_sequence=[0]
        )

        rejected(events, Rejection.NOT_YOUR_TURN)
        assert events[0].to == (waiting,)

    def test_wrong_turn_number(self) -> None:
        state = started()
        active = with_hand(state, *cab())

        _, events = act(
            state, active, ActionType.CAST_WORD, turn=2, glyph_sequence=[0, 1, 2]
        )

        rejected(events, Rejection.WRONG_TURN)
        assert events[0].data == {
            "action": "CAST_WORD",
            "turn": 2,
            "code": "WRONG_TURN",
            "reason": "It is turn 1.",
        }

    def test_draft_actions_during_action_phase(self) -> None:
        state = started()

        _, events = act(state, state.active_player, ActionType.REROLL_PERKS, turn=1)

        rejected(events, Rejection.WRONG_PHASE)

    @pytest.mark.parametrize(
        "data",
        [
            {"glyph_sequence": [0]},
            {"turn": "1", "glyph_sequence": [0]},
            {"turn": 1, "glyph_sequence": "CAB"},
            {"turn": 1, "glyph_sequence": [0, "1"]},
            {"turn": 1, "glyph_sequence": [True]},
            {"turn": 1},
        ],
    )
    def test_malformed_cast(self, data: dict) -> None:  # type: ignore[type-arg]
        state = started()
        active = with_hand(state, *cab())

        _, events = apply(state, Action(active, ActionType.CAST_WORD, data), 0, RULES)

        rejected(events, Rejection.MALFORMED)

    def test_unknown_word(self) -> None:
        state = started()
        active = with_hand(state, *cab())

        _, events = act(
            state, active, ActionType.CAST_WORD, turn=1, glyph_sequence=[2, 0, 1]
        )

        rejected(events, "UNKNOWN_WORD")

    def test_rejection_returns_the_same_untouched_state(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        before = state.to_dict()

        after, _ = act(
            state, active, ActionType.CAST_WORD, turn=1, glyph_sequence=[0, 0]
        )

        assert after is state
        assert state.to_dict() == before

    def test_success_does_not_change_the_given_state(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        before = state.to_dict()

        after, _ = act(
            state, active, ActionType.CAST_WORD, turn=1, glyph_sequence=[0, 1, 2]
        )

        assert after is not state
        assert state.to_dict() == before
        assert after.turn == 2

    def test_unknown_player_index_is_a_programming_error(self) -> None:
        with pytest.raises(ValueError):
            act(started(), 2, ActionType.PLAYER_READY)


class TestApplyPerk:
    def test_changes_the_glyph_and_tells_only_the_player(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        instance = grant_perk(state, active, "amplify")

        state, events = act(
            state,
            active,
            ActionType.APPLY_PERK,
            turn=1,
            glyph_index=2,
            perk_instance_id=instance.instance_id,
        )

        [event] = events
        assert event.type == EventType.PERK_APPLIED
        assert event.to == (active,)
        assert event.data["perk_instance_id"] == instance.instance_id
        assert event.data["durability_left"] == 3
        assert event.data["glyph"]["value"] == 40
        assert state.players[active].hand[2].value == 40
        assert state.phase == Phase.ACTION

    def test_perk_errors_are_rejections(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        instance = grant_perk(state, active, "amplify")

        _, events = act(
            state,
            active,
            ActionType.APPLY_PERK,
            turn=1,
            glyph_index=1,  # A is a SKILL glyph
            perk_instance_id=instance.instance_id,
        )

        rejected(events, "WRONG_TARGET")

    @pytest.mark.parametrize("index", [-1, 3])
    def test_glyph_index_must_be_in_hand(self, index: int) -> None:
        state = started()
        active = with_hand(state, *cab())
        instance = grant_perk(state, active, "amplify")

        _, events = act(
            state,
            active,
            ActionType.APPLY_PERK,
            turn=1,
            glyph_index=index,
            perk_instance_id=instance.instance_id,
        )

        rejected(events, Rejection.MALFORMED)


class TestCast:
    def test_resolves_and_passes_the_turn_when_nothing_can_be_drafted(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        other = 1 - active

        state, events = act(
            state, active, ActionType.CAST_WORD, turn=1, glyph_sequence=[0, 1, 2]
        )

        assert types(events) == ["WORD_RESOLVED", "TURN_START", "OPPONENT_TURN_START"]
        resolved = events[0]
        assert resolved.to == (0, 1)
        assert resolved.data["word"] == "CAB"
        assert resolved.data["player_id"] == USERS[active]
        assert resolved.data["turn"] == 1
        assert resolved.data["totals"] == {"damage": 32, "defense": 0, "heal": 10}
        assert state.players[other].hp == 68
        assert (state.turn, state.active_player, state.phase) == (
            2,
            other,
            Phase.ACTION,
        )
        assert events[1].to == (other,)
        assert len(state.players[other].hand) == 7
        assert state.players[active].hand == []
        assert {g.id for g in cab()} <= {
            g.id for g in state.players[active].discard_pile
        }

    def test_achievement_words_count(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        rules = MatchRules(frozenset(), achievement_words=["cab"])

        _, events = act(
            state, active, ActionType.CAST_WORD, rules, turn=1, glyph_sequence=[0, 1, 2]
        )

        assert events[0].type == EventType.WORD_RESOLVED

    def test_knockout_ends_the_match(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        state.players[1 - active].hp = 30

        state, events = act(
            state, active, ActionType.CAST_WORD, turn=1, glyph_sequence=[0, 1, 2]
        )

        assert types(events) == ["WORD_RESOLVED", "MATCH_ENDED"]
        assert events[1].to == (0, 1)
        assert events[1].data["winner_id"] == USERS[active]
        assert events[1].data["end_reason"] == "HEALTH_DEPLETED"
        assert state.phase == Phase.ENDED
        assert (state.winner, state.end_reason) == (active, EndReason.HEALTH_DEPLETED)

    def test_nothing_is_accepted_after_the_end(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        state.players[1 - active].hp = 1
        state, _ = act(
            state, active, ActionType.CAST_WORD, turn=1, glyph_sequence=[0, 1, 2]
        )

        _, events = act(state, active, ActionType.REROLL_PERKS, turn=1)

        rejected(events, Rejection.MATCH_ENDED)


class TestDraft:
    def cast(self) -> tuple[MatchState, int, list]:  # type: ignore[type-arg]
        state = started(rules=DRAFTING)
        active = with_hand(state, *cab())
        state, events = act(
            state,
            active,
            ActionType.CAST_WORD,
            DRAFTING,
            turn=1,
            glyph_sequence=[0, 1, 2],
        )
        return state, active, events

    def test_cast_opens_a_private_draft(self) -> None:
        state, active, events = self.cast()

        assert types(events) == ["WORD_RESOLVED", "PERK_DRAFT_OPTIONS"]
        draft = events[1]
        assert draft.to == (active,)
        assert len(draft.data["options"]) == 3
        assert draft.data["pick_count"] == 1
        assert draft.data["rerolls_left"] == 3
        assert (state.phase, state.turn) == (Phase.DRAFT, 1)

    def test_hand_is_discarded_once_cast(self) -> None:
        state, active, _ = self.cast()

        assert state.players[active].hand == []
        assert {g.id for g in cab()} <= {
            g.id for g in state.players[active].discard_pile
        }

    def test_cannot_cast_again_while_drafting(self) -> None:
        state, active, _ = self.cast()

        _, events = act(
            state, active, ActionType.CAST_WORD, DRAFTING, turn=1, glyph_sequence=[0]
        )

        rejected(events, Rejection.WRONG_PHASE)

    def test_reroll(self) -> None:
        state, active, _ = self.cast()

        state, events = act(state, active, ActionType.REROLL_PERKS, DRAFTING, turn=1)

        [event] = events
        assert event.type == EventType.PERK_DRAFT_OPTIONS
        assert event.data["rerolls_left"] == 2
        assert [o["perk_id"] for o in event.data["options"]] == state.players[
            active
        ].draft_offer

    def test_select_by_perk_id_ends_the_turn(self) -> None:
        state, active, events = self.cast()
        chosen = events[1].data["options"][1]["perk_id"]

        state, events = act(
            state, active, ActionType.SELECT_PERKS, DRAFTING, turn=1, perk_ids=[chosen]
        )

        assert types(events) == ["TURN_START", "OPPONENT_TURN_START"]
        assert [p.perk_id for p in state.players[active].perks] == [chosen]
        assert state.players[active].draft_offer == []
        assert (state.turn, state.active_player) == (2, 1 - active)

    def test_perk_not_on_offer(self) -> None:
        state, active, _ = self.cast()
        offered = set(state.players[active].draft_offer)
        missing = next(pid for pid in ALL_READY if pid not in offered)

        _, events = act(
            state, active, ActionType.SELECT_PERKS, DRAFTING, turn=1, perk_ids=[missing]
        )

        rejected(events, Rejection.NOT_OFFERED)

    def test_wrong_number_of_picks(self) -> None:
        state, active, _ = self.cast()

        _, events = act(
            state,
            active,
            ActionType.SELECT_PERKS,
            DRAFTING,
            turn=1,
            perk_ids=state.players[active].draft_offer[:2],
        )

        rejected(events, "WRONG_PICK_COUNT")

    def test_no_rerolls_left(self) -> None:
        state, active, _ = self.cast()
        for _ in range(3):
            state, _ = act(state, active, ActionType.REROLL_PERKS, DRAFTING, turn=1)

        _, events = act(state, active, ActionType.REROLL_PERKS, DRAFTING, turn=1)

        rejected(events, "NO_REROLLS_LEFT")


class TestBetweenTurns:
    def pass_turn(self, state: MatchState, *hand: Glyph, word: list[int]) -> MatchState:
        active = with_hand(state, *hand)
        state, events = act(
            state, active, ActionType.CAST_WORD, turn=state.turn, glyph_sequence=word
        )
        assert events[0].type == EventType.WORD_RESOLVED, events
        return state

    def test_statuses_last_the_next_two_turns(self) -> None:
        state = started()
        attacker = state.active_player
        target = 1 - attacker
        eve = (
            g(0, "E", S, Effect.WEAK, 2),
            g(1, "V", S, Effect.VULNERABLE, 2),
            g(2, "E", S, Effect.WEAK, 2),
        )

        # Turn 1: attacker makes the target Weak and Vulnerable.
        state = self.pass_turn(state, *eve, word=[0, 1, 2])
        assert {(s.effect, s.turns_left) for s in state.players[target].statuses} == {
            (Effect.WEAK, 2),
            (Effect.VULNERABLE, 2),
        }

        # Turn 2: the target is Weak; its power glyph loses 25%.
        state = self.pass_turn(
            state, g(3, "A", S, Effect.HEAL, 1), g(4, "T", value=8), word=[0, 1]
        )
        assert state.players[attacker].hp == 100 - 6
        assert {s.turns_left for s in state.players[target].statuses} == {1}

        # Turn 3: the target is still Vulnerable; the attacker's hit grows 25%.
        state = self.pass_turn(
            state, g(5, "A", S, Effect.HEAL, 0), g(6, "T", value=8), word=[0, 1]
        )
        assert state.players[target].hp == 100 - 10
        assert state.players[target].statuses == []

    def test_reapplied_status_counts_from_the_new_turn(self) -> None:
        state = started()
        attacker = state.active_player
        target = 1 - attacker
        # Left over from earlier: one turn of Vulnerable.
        state.players[target].statuses = [Status(Effect.VULNERABLE, 1, 0)]
        vee = (
            g(0, "A", S, Effect.HEAL, 0),
            g(1, "T", S, Effect.VULNERABLE, 2),
        )

        state = self.pass_turn(state, *vee, word=[0, 1])

        # Extended to 2 in turn 1, so the end of turn 1 doesn't count.
        assert state.players[target].statuses == [Status(Effect.VULNERABLE, 2, 1)]

    def test_defense_resets_at_the_start_of_its_owners_turn(self) -> None:
        state = started()
        first = state.active_player
        state = self.pass_turn(
            state,
            g(0, "A", S, Effect.HEAL, 0),
            g(1, "T", S, Effect.DEFENSE, 15),
            word=[0, 1],
        )
        # The opponent's turn: the Defense is still there and absorbs 10.
        assert state.players[first].defense == 15
        second = with_hand(state, g(2, "A", S, Effect.HEAL, 0), g(3, "T", value=10))

        state, events = act(
            state, second, ActionType.CAST_WORD, turn=2, glyph_sequence=[0, 1]
        )

        assert events[0].data["damage_blocked"] == 10
        assert events[0].data["target_after"]["defense"] == 5
        # Then the first player's turn starts, and the rest is gone.
        assert state.active_player == first
        assert state.players[first].defense == 0
        assert state.players[first].hp == 100

    def test_defense_can_carry_over(self) -> None:
        rules = MatchRules(WORDS, config=GameConfig(defense_carries_over=True))
        state = started(rules=rules)
        first = with_hand(
            state, g(0, "A", S, Effect.HEAL, 0), g(1, "T", S, Effect.DEFENSE, 15)
        )
        state, _ = act(
            state, first, ActionType.CAST_WORD, rules, turn=1, glyph_sequence=[0, 1]
        )
        second = with_hand(
            state, g(2, "A", S, Effect.HEAL, 0), g(3, "T", S, Effect.HEAL, 0)
        )
        state, _ = act(
            state, second, ActionType.CAST_WORD, rules, turn=2, glyph_sequence=[0, 1]
        )

        assert state.active_player == first
        assert state.players[first].defense == 15

    def test_glyphs_are_never_lost_over_many_turns(self) -> None:
        state = started()
        totals = [len(p.all_glyphs()) for p in state.players]
        for turn in range(1, 25):
            active = state.active_player
            hand = state.players[active].hand
            # Cast "AT" from any A/T pair, else rewrite two glyphs into a word.
            hand[0].letters, hand[1].letters = "A", "T"
            state, events = act(
                state, active, ActionType.CAST_WORD, turn=turn, glyph_sequence=[0, 1]
            )
            assert events[0].type == EventType.WORD_RESOLVED
            if state.phase == Phase.ENDED:
                break
        assert [len(p.all_glyphs()) for p in state.players] == totals


class TestMatchState:
    def test_hand_only_on_your_own_turn(self) -> None:
        state = started()
        active = state.active_player

        mine = match_state(state, active)
        theirs = match_state(state, 1 - active)

        assert mine.to == (active,)
        assert len(mine.data["hand"]) == 7
        assert theirs.data["hand"] is None
        assert theirs.data["draft_offer"] is None
        assert theirs.data["players"][active]["hand_size"] == 7
        assert mine.data["active_player_id"] == USERS[active]
        json.dumps(mine.data)

    def test_counts_and_perks(self) -> None:
        state = started()
        active = state.active_player
        grant_perk(state, active, "amplify")

        data = match_state(state, active).data

        assert data["players"][active]["draw_count"] == 33
        assert data["players"][active]["discard_count"] == 0
        assert [p["perk_id"] for p in data["perks"]] == ["amplify"]
        assert data["rerolls_left"] == 3
        assert data["winner_id"] is None

    def test_after_the_end(self) -> None:
        state = started()
        active = with_hand(state, *cab())
        state.players[1 - active].hp = 1
        state, _ = act(
            state, active, ActionType.CAST_WORD, turn=1, glyph_sequence=[0, 1, 2]
        )

        data = match_state(state, active).data

        assert data["phase"] == "ENDED"
        assert data["hand"] is None
        assert data["winner_id"] == USERS[active]
        assert data["end_reason"] == "HEALTH_DEPLETED"


class TestParseAction:
    def test_known_action(self) -> None:
        action = parse_action(
            1, {"type": "CAST_WORD", "data": {"turn": 3, "glyph_sequence": [0]}}
        )

        assert action == Action(
            1, ActionType.CAST_WORD, {"turn": 3, "glyph_sequence": [0]}
        )

    @pytest.mark.parametrize(
        "kind", ["SEND_MESSAGE", "PING", "SURRENDER", "cast_word", None, 5]
    )
    def test_other_messages_are_not_match_actions(self, kind: object) -> None:
        assert parse_action(0, {"type": kind, "data": {}}) is None

    def test_missing_data_becomes_empty(self) -> None:
        assert parse_action(0, {"type": "PLAYER_READY", "data": "x"}) == Action(
            0, ActionType.PLAYER_READY, {}
        )

    def test_status_carries_the_turn_it_was_applied(self) -> None:
        state = started()
        attacker = with_hand(
            state,
            g(0, "E", S, Effect.WEAK, 2),
            g(1, "V", S, Effect.VULNERABLE, 2),
            g(2, "E", S, Effect.WEAK, 2),
        )

        state, _ = act(
            state, attacker, ActionType.CAST_WORD, turn=1, glyph_sequence=[0, 1, 2]
        )

        assert all(s.applied_turn == 1 for s in state.players[1 - attacker].statuses)
        assert Status(Effect.WEAK, 2, 1) in state.players[1 - attacker].statuses
