"""Resolving cast words: per-glyph stages, totals, statuses and the log."""

import json

import pytest

pytest.importorskip("backend.game.resolution", reason="Resolution is not merged yet")

from backend.game.config import DEFAULT_CONFIG, Effect, GlyphType
from backend.game.piles import new_match
from backend.game.resolution import Stage, WordContext, resolve_word
from backend.game.spelling import SpellingError, SpellingProblem
from backend.game.state import Glyph, MatchState, Status

P, S = GlyphType.POWER, GlyphType.SKILL
D, DEF, H = Effect.DAMAGE, Effect.DEFENSE, Effect.HEAL
V, W = Effect.VULNERABLE, Effect.WEAK


def g(n: int, letters: str, type_: GlyphType, effect: Effect, value: int) -> Glyph:
    return Glyph(f"p0-g{n}", letters, type_, effect, value)


def match(*hand: Glyph, caster: int = 0) -> MatchState:
    state = new_match("match-1", ("user-a", "user-b"), 180, seed="seed")
    state.players[caster].hand = list(hand)
    return state


def brave() -> list[Glyph]:
    # The GDD example. B's 20 was doubled to 40 by a perk applied earlier.
    return [
        g(0, "B", P, D, 40),
        g(1, "R", S, DEF, 15),
        g(2, "A", S, H, 10),
        g(3, "V", S, V, 2),
        g(4, "E", S, W, 2),
    ]


class TestGddExample:
    def test_totals_and_effects(self) -> None:
        state = match(*brave())
        state.players[0].hp = 80

        result = resolve_word(state, 0, [0, 1, 2, 3, 4])

        assert result.word == "BRAVE"
        assert (result.caster, result.target) == (0, 1)
        assert (result.damage, result.defense, result.heal) == (40, 15, 10)
        assert state.players[1].hp == 60
        assert state.players[0].defense == 15
        assert state.players[0].hp == 90
        assert {(s.effect, s.turns_left) for s in state.players[1].statuses} == {
            (V, 2),
            (W, 2),
        }
        assert state.players[0].statuses == []

    def test_statuses_from_the_word_do_not_change_its_own_glyphs(self) -> None:
        # V comes before B, but Vulnerable only counts from the next word.
        state = match(g(0, "V", S, V, 2), g(1, "B", P, D, 20))

        result = resolve_word(state, 0, [0, 1])

        assert result.damage == 20
        assert result.steps[1].changes == ()

    def test_next_word_feels_the_statuses(self) -> None:
        state = match(*brave())
        resolve_word(state, 0, [0, 1, 2, 3, 4])

        # The target is now Weak and Vulnerable; it casts back.
        state.players[0].defense = 0
        state.players[1].hand = [g(9, "T", P, D, 8)]
        result = resolve_word(state, 1, [0])

        # Its own Weak lowers its Power glyph: 8 -> 6. The caster isn't Vulnerable.
        assert [c.stage for c in result.steps[0].changes] == [Stage.WEAK]
        assert result.damage == 6
        assert state.players[0].hp == DEFAULT_CONFIG.max_hp - 6


class TestStages:
    def test_vulnerable_target_takes_more_damage_rounded_down(self) -> None:
        state = match(g(0, "D", P, D, 10))
        state.players[1].statuses = [Status(V, 1)]

        result = resolve_word(state, 0, [0])

        assert result.steps[0].final_value == 12
        assert result.damage == 12

    def test_vulnerable_only_raises_damage(self) -> None:
        state = match(g(0, "R", S, DEF, 15), g(1, "A", S, H, 10))
        state.players[1].statuses = [Status(V, 2)]

        result = resolve_word(state, 0, [0, 1])

        assert [s.final_value for s in result.steps] == [15, 10]

    def test_weak_caster_lowers_power_glyphs_only(self) -> None:
        state = match(
            g(0, "S", P, D, 8),
            g(1, "R", S, DEF, 15),
            g(2, "K", P, H, 12),  # a Power glyph a perk turned into healing
        )
        state.players[0].hp = 50
        state.players[0].statuses = [Status(W, 2)]

        result = resolve_word(state, 0, [0, 1, 2])

        assert [s.final_value for s in result.steps] == [6, 15, 9]
        assert result.steps[0].changes[0].stage == Stage.WEAK

    def test_weak_comes_before_vulnerable(self) -> None:
        # 9 -> 6 (Weak) -> 7 (Vulnerable). The other order would give 8.
        state = match(g(0, "X", P, D, 9))
        state.players[0].statuses = [Status(W, 1)]
        state.players[1].statuses = [Status(V, 1)]

        step = resolve_word(state, 0, [0]).steps[0]

        assert [(c.stage, c.before, c.after) for c in step.changes] == [
            (Stage.WEAK, 9, 6),
            (Stage.VULNERABLE, 6, 7),
        ]
        assert step.value == 9
        assert step.final_value == 7

    def test_expired_statuses_do_nothing(self) -> None:
        state = match(g(0, "D", P, D, 10))
        state.players[0].statuses = [Status(W, 0)]
        state.players[1].statuses = [Status(V, 0)]

        assert resolve_word(state, 0, [0]).damage == 10

    def test_status_glyph_durations_are_never_changed(self) -> None:
        glyph = g(0, "V", S, V, 2)
        glyph.conditional_slot = "plus_five_at_end"  # no rule passed: not looked up
        state = match(glyph)
        state.players[0].statuses = [Status(W, 2)]
        state.players[1].statuses = [Status(V, 1)]

        result = resolve_word(state, 0, [0])

        assert result.steps[0].changes == ()
        assert state.players[1].statuses == [Status(V, 2)]


def plus_five_at_end(glyph: Glyph, ctx: WordContext, value: int) -> int:
    return value + 5 if ctx.is_last else value


class TestConditionalSlot:
    def test_rule_is_applied_and_logged_with_the_perk(self) -> None:
        first = g(0, "S", P, D, 8)
        last = g(1, "T", P, D, 8)
        first.conditional_slot = last.conditional_slot = "plus_five_at_end"
        state = match(first, last)

        result = resolve_word(
            state, 0, [0, 1], conditionals={"plus_five_at_end": plus_five_at_end}
        )

        assert result.steps[0].changes == ()
        (change,) = result.steps[1].changes
        assert (change.stage, change.before, change.after, change.perk_id) == (
            Stage.CONDITIONAL,
            8,
            13,
            "plus_five_at_end",
        )
        assert result.damage == 21

    def test_rule_sees_the_word_and_position(self) -> None:
        seen: list[tuple[str, int, bool, bool]] = []

        def spy(glyph: Glyph, ctx: WordContext, value: int) -> int:
            seen.append((ctx.word, ctx.index, ctx.is_first, ctx.is_last))
            assert ctx.glyphs[ctx.index] is glyph
            return value

        middle = g(1, "ING", P, D, 8)
        middle.conditional_slot = "spy"
        state = match(g(0, "S", P, D, 8), middle, g(2, "S", P, D, 8))

        resolve_word(state, 0, [0, 1, 2], conditionals={"spy": spy})

        assert seen == [("SINGS", 1, False, False)]

    def test_conditional_comes_before_weak(self) -> None:
        glyph = g(0, "S", P, D, 8)
        glyph.conditional_slot = "plus_five_at_end"
        state = match(glyph)
        state.players[0].statuses = [Status(W, 1)]

        result = resolve_word(
            state, 0, [0], conditionals={"plus_five_at_end": plus_five_at_end}
        )

        # (8 + 5) -> 9 after Weak. Weak first would give 6 + 5 = 11.
        assert result.steps[0].final_value == 9

    def test_rule_cannot_push_value_below_zero(self) -> None:
        glyph = g(0, "S", P, D, 8)
        glyph.conditional_slot = "minus"
        state = match(glyph)

        result = resolve_word(
            state, 0, [0], conditionals={"minus": lambda g, c, v: v - 100}
        )

        assert result.steps[0].final_value == 0
        assert state.players[1].hp == DEFAULT_CONFIG.max_hp

    def test_missing_rule_raises_and_changes_nothing(self) -> None:
        glyph = g(0, "S", P, D, 8)
        glyph.conditional_slot = "unknown_perk"
        state = match(glyph)
        before = state.to_dict()

        with pytest.raises(ValueError, match="unknown_perk"):
            resolve_word(state, 0, [0])

        assert state.to_dict() == before


class TestApplying:
    def test_defense_absorbs_damage_first(self) -> None:
        state = match(g(0, "B", P, D, 20))
        state.players[1].defense = 15

        result = resolve_word(state, 0, [0])

        assert (result.damage_blocked, result.hp_damage) == (15, 5)
        assert state.players[1].defense == 0
        assert state.players[1].hp == DEFAULT_CONFIG.max_hp - 5

    def test_damage_smaller_than_defense_leaves_hp_alone(self) -> None:
        state = match(g(0, "S", P, D, 8))
        state.players[1].defense = 15

        result = resolve_word(state, 0, [0])

        assert (result.damage_blocked, result.hp_damage) == (8, 0)
        assert state.players[1].defense == 7
        assert state.players[1].hp == DEFAULT_CONFIG.max_hp

    def test_hp_stops_at_zero_and_reports_defeat(self) -> None:
        state = match(g(0, "Z", P, D, 25))
        state.players[1].hp = 10

        result = resolve_word(state, 0, [0])

        assert state.players[1].hp == 0
        assert result.hp_damage == 10
        assert result.target_defeated is True

    def test_not_defeated_while_hp_left(self) -> None:
        state = match(g(0, "S", P, D, 8))
        assert resolve_word(state, 0, [0]).target_defeated is False

    def test_heal_is_capped_at_max_hp(self) -> None:
        state = match(g(0, "A", S, H, 10), g(1, "Y", S, H, 14))
        state.players[0].hp = DEFAULT_CONFIG.max_hp - 5

        result = resolve_word(state, 0, [0, 1])

        assert result.heal == 24
        assert result.hp_healed == 5
        assert state.players[0].hp == DEFAULT_CONFIG.max_hp

    def test_defense_adds_to_existing_defense(self) -> None:
        state = match(g(0, "O", S, DEF, 10))
        state.players[0].defense = 4

        resolve_word(state, 0, [0])

        assert state.players[0].defense == 14

    def test_second_player_targets_the_first(self) -> None:
        state = match(g(0, "S", P, D, 8), caster=1)

        result = resolve_word(state, 1, [0])

        assert (result.caster, result.target) == (1, 0)
        assert state.players[0].hp == DEFAULT_CONFIG.max_hp - 8
        assert state.players[1].hp == DEFAULT_CONFIG.max_hp


class TestStatusesApplied:
    def test_longer_existing_status_is_kept(self) -> None:
        state = match(g(0, "V", S, V, 2))
        state.players[1].statuses = [Status(V, 3)]

        resolve_word(state, 0, [0])

        assert state.players[1].statuses == [Status(V, 3)]

    def test_shorter_existing_status_is_extended(self) -> None:
        state = match(g(0, "V", S, V, 2))
        state.players[1].statuses = [Status(V, 1)]

        resolve_word(state, 0, [0])

        assert state.players[1].statuses == [Status(V, 2)]

    def test_same_status_twice_in_a_word_does_not_stack(self) -> None:
        state = match(g(0, "E", S, W, 2), g(1, "E", S, W, 3))

        result = resolve_word(state, 0, [0, 1])

        assert result.statuses_applied == (Status(W, 3),)
        assert state.players[1].statuses == [Status(W, 3)]


class TestInputs:
    def test_hand_and_piles_are_left_alone(self) -> None:
        hand = brave()
        state = match(*hand)
        draw_pile = list(state.players[0].draw_pile)

        resolve_word(state, 0, [0, 1])

        assert state.players[0].hand == hand
        assert state.players[0].draw_pile == draw_pile
        assert state.players[0].discard_pile == []

    def test_uses_positions_in_the_order_given(self) -> None:
        state = match(g(0, "T", P, D, 8), g(1, "A", S, H, 10))
        assert resolve_word(state, 0, [1, 0]).word == "AT"

    @pytest.mark.parametrize(
        ("positions", "problem"),
        [
            ([], SpellingProblem.NO_GLYPHS),
            ([5], SpellingProblem.POSITION_OUT_OF_RANGE),
            ([0, 0], SpellingProblem.REPEATED_POSITION),
        ],
    )
    def test_bad_positions_raise_and_change_nothing(
        self, positions: list[int], problem: SpellingProblem
    ) -> None:
        state = match(*brave())
        before = state.to_dict()

        with pytest.raises(SpellingError) as caught:
            resolve_word(state, 0, positions)

        assert caught.value.problem == problem
        assert state.to_dict() == before


class TestPayload:
    def test_is_json_safe_and_complete(self) -> None:
        first = g(0, "B", P, D, 40)
        first.conditional_slot = "plus_five_at_end"
        state = match(first, *brave()[1:])
        state.players[1].defense = 5

        result = resolve_word(
            state,
            0,
            [0, 1, 2, 3, 4],
            conditionals={"plus_five_at_end": plus_five_at_end},
        )
        payload = json.loads(json.dumps(result.to_dict()))

        assert payload["word"] == "BRAVE"
        assert payload["totals"] == {"damage": 40, "defense": 15, "heal": 10}
        assert payload["damage_blocked"] == 5
        assert payload["hp_damage"] == 35
        assert payload["hp_healed"] == 0
        assert payload["target_defeated"] is False
        assert payload["steps"][0] == {
            "glyph_id": "p0-g0",
            "letters": "B",
            "type": "POWER",
            "effect": "DAMAGE",
            "value": 40,
            "changes": [],
            "final_value": 40,
        }
        assert payload["statuses_applied"] == [
            {"effect": "VULNERABLE", "turns_left": 2, "applied_turn": 0},
            {"effect": "WEAK", "turns_left": 2, "applied_turn": 0},
        ]
        assert payload["caster_after"] == {"hp": 100, "defense": 15, "statuses": []}
        assert payload["target_after"]["hp"] == 65
        assert payload["target_after"]["defense"] == 0
        assert len(payload["target_after"]["statuses"]) == 2

    def test_changes_are_in_the_payload(self) -> None:
        state = match(g(0, "D", P, D, 10))
        state.players[1].statuses = [Status(V, 1)]

        step = resolve_word(state, 0, [0]).to_dict()["steps"][0]

        assert step["changes"] == [
            {"stage": "VULNERABLE", "before": 10, "after": 12, "perk_id": None}
        ]
