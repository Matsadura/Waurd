"""Every perk in the catalog does what its sheet row says."""

import pytest

pytest.importorskip("backend.game.perks", reason="Perks are not merged yet")

from backend.game.config import DEFAULT_CONFIG, Effect, GlyphType
from backend.game.perks import apply_perk, grant_perk, load_catalog, registered
from backend.game.piles import new_match
from backend.game.resolution import resolve_word
from backend.game.state import Glyph, MatchState, Status

P, S = GlyphType.POWER, GlyphType.SKILL
D, DEF, H = Effect.DAMAGE, Effect.DEFENSE, Effect.HEAL
V, W = Effect.VULNERABLE, Effect.WEAK
HP = DEFAULT_CONFIG.max_hp


def g(
    n: int, letters: str, type_: GlyphType = P, effect: Effect = D, value: int = 8
) -> Glyph:
    return Glyph(f"p0-h{n}", letters, type_, effect, value)


def match(*hand: Glyph, seed: str = "seed") -> MatchState:
    state = new_match("match-1", ("user-a", "user-b"), 180, seed=seed)
    for player in state.players:
        player.defense = 0
    state.players[0].hand = list(hand)
    return state


def use(state: MatchState, perk_id: str, glyph_id: str = "p0-h0"):  # type: ignore[no-untyped-def]
    instance = grant_perk(state, 0, perk_id)
    return apply_perk(state, 0, instance.instance_id, glyph_id)


def first(state: MatchState) -> Glyph:
    return state.players[0].hand[0]


class TestValuePerks:
    @pytest.mark.parametrize(
        ("perk_id", "before", "after"),
        [
            ("sharpen", 8, 12),
            ("round_up", 8, 10),
            ("round_up", 10, 15),
            ("amplify", 9, 13),
            ("overcharge", 10, 25),
            ("blood", 8, 23),
        ],
    )
    def test_power_values(self, perk_id: str, before: int, after: int) -> None:
        state = match(g(0, "T", value=before))

        assert use(state, perk_id).applied is True
        assert first(state).value == after

    def test_fortify_adds_6_to_defense_or_heal(self) -> None:
        state = match(g(0, "R", S, DEF, 14))
        use(state, "fortify")
        assert first(state).value == 20

    @pytest.mark.parametrize("effect", [V, W])
    def test_fortify_leaves_status_glyphs_alone(self, effect: Effect) -> None:
        state = match(g(0, "E", S, effect, 2))

        result = use(state, "fortify")

        assert result.applied is False
        assert result.durability_left == 4
        assert first(state).value == 2

    def test_snowball_grows_with_each_use(self) -> None:
        state = match(g(0, "T", value=0))
        instance = grant_perk(state, 0, "snowball")

        values = []
        for _ in range(4):
            apply_perk(state, 0, instance.instance_id, "p0-h0")
            values.append(first(state).value)

        assert values == [3, 9, 18, 30]

    def test_blood_costs_8_hp_but_never_kills(self) -> None:
        state = match(g(0, "T"))
        use(state, "blood")
        assert state.players[0].hp == HP - 8

        state = match(g(0, "T"))
        state.players[0].hp = 5
        use(state, "blood")
        assert state.players[0].hp == 1

    def test_double_or_halve_doubles_more_often(self) -> None:
        doubled = 0
        for seed in range(600):
            state = match(g(0, "T", value=10), seed=f"d{seed}")
            use(state, "double_or_halve")
            assert first(state).value in (20, 5)
            doubled += first(state).value == 20
        assert 0.55 < doubled / 600 < 0.66


class TestLetterPerks:
    @pytest.mark.parametrize(
        ("perk_id", "letters", "bonus"),
        [
            ("ing", "ING", 7),
            ("er", "ER", 5),
            ("re", "RE", 5),
            ("ed", "ED", 5),
            ("pluralize", "S", 3),
            ("qu", "QU", 18),
        ],
    )
    def test_transform(self, perk_id: str, letters: str, bonus: int) -> None:
        state = match(g(0, "T", value=8))

        use(state, perk_id)

        assert (first(state).letters, first(state).value) == (letters, 8 + bonus)

    @pytest.mark.parametrize(
        ("perk_id", "letters"), [("ed", "ED"), ("pluralize", "S"), ("qu", "QU")]
    )
    def test_transform_to_the_same_letters_does_nothing(
        self, perk_id: str, letters: str
    ) -> None:
        state = match(g(0, letters, value=8))

        assert use(state, perk_id).applied is False
        assert first(state).value == 8

    @pytest.mark.parametrize(
        ("perk_id", "pool", "bonus"),
        [("vowel_shift", set("AEIOU"), 2), ("consonant_shift", set("STNRLD"), 4)],
    )
    def test_shifts(self, perk_id: str, pool: set[str], bonus: int) -> None:
        seen = set()
        for seed in range(40):
            state = match(g(0, "A", S, H, 9), seed=f"s{seed}")

            use(state, perk_id)

            glyph = first(state)
            assert glyph.letters in pool and glyph.letters != "A"
            assert (glyph.type, glyph.effect, glyph.value) == (S, H, 9 + bonus)
            seen.add(glyph.letters)
        assert len(seen) > 2


class TestTypeAndEffectPerks:
    def test_wild_power_makes_a_damage_glyph(self) -> None:
        state = match(g(0, "A", S, H, 9))

        use(state, "wild_power")

        assert (first(state).type, first(state).effect, first(state).value) == (
            P,
            D,
            13,
        )

    def test_wild_power_skips_status_glyphs(self) -> None:
        state = match(g(0, "V", S, V, 2))
        assert use(state, "wild_power").applied is False
        assert first(state).effect == V

    def test_wild_skill_makes_defense_or_heal(self) -> None:
        effects = set()
        for seed in range(30):
            state = match(g(0, "T", value=9), seed=f"w{seed}")
            use(state, "wild_skill")
            glyph = first(state)
            assert glyph.type == S and glyph.value == 15
            effects.add(glyph.effect)
        assert effects == {DEF, H}

    @pytest.mark.parametrize(("perk_id", "effect"), [("hex", W), ("expose", V)])
    def test_curses_go_on_the_opponent_for_3_turns(
        self, perk_id: str, effect: Effect
    ) -> None:
        state = match(g(0, "T"))
        state.turn = 4

        result = use(state, perk_id)

        assert result.applied is True
        assert state.players[1].statuses == [Status(effect, 3, 4)]
        assert state.players[0].statuses == []
        assert (first(state).effect, first(state).value) == (D, 8)

    def test_expose_already_counts_for_this_word(self) -> None:
        state = match(g(0, "T", value=8), g(1, "A", S, H, 0))
        use(state, "expose")

        result = resolve_word(state, 0, [1, 0])

        assert result.damage == 10  # 8 + 25%

    def test_linger_lengthens_every_opponent_status(self) -> None:
        state = match(g(0, "T"))
        state.players[1].statuses = [Status(W, 1, 0), Status(V, 2, 0)]

        use(state, "linger")

        assert [s.turns_left for s in state.players[1].statuses] == [3, 4]

    def test_linger_without_statuses_weakens(self) -> None:
        state = match(g(0, "T"))
        use(state, "linger")
        assert [(s.effect, s.turns_left) for s in state.players[1].statuses] == [(W, 2)]


class TestDeckPerks:
    def test_erase_draws_a_replacement(self) -> None:
        state = match(g(0, "Z"), g(1, "A"))
        draw_before = len(state.players[0].draw_pile)

        use(state, "erase")

        side = state.players[0]
        assert "p0-h0" not in {x.id for x in side.all_glyphs()}
        assert len(side.hand) == 2
        assert len(side.draw_pile) == draw_before - 1

    def test_redraw_discards_and_draws_a_stronger_glyph(self) -> None:
        state = match(g(0, "Z"), g(1, "A"))
        top = state.players[0].draw_pile[-1]
        top_value = top.value

        use(state, "redraw")

        side = state.players[0]
        assert [x.id for x in side.discard_pile] == ["p0-h0"]
        assert side.hand[-1].id == top.id
        expected = top_value if top.effect in (V, W) else top_value + 5
        assert side.hand[-1].value == expected

    def test_fresh_start_replaces_the_whole_hand(self) -> None:
        state = match(g(0, "Z"), g(1, "A"), g(2, "B"))
        coming = list(reversed(state.players[0].draw_pile[-7:]))
        values = {x.id: x.value for x in coming}

        use(state, "fresh_start")

        side = state.players[0]
        assert {x.id for x in side.discard_pile} == {"p0-h0", "p0-h1", "p0-h2"}
        assert [x.id for x in side.hand] == [x.id for x in coming]
        for glyph in side.hand:
            bonus = 0 if glyph.effect in (V, W) else 3
            assert glyph.value == values[glyph.id] + bonus


def cast(
    letters: list[str],
    slot_at: int,
    perk_id: str,
    *,
    value: int = 8,
    caster_hp: int = HP,
    target_hp: int = HP,
    types: list[GlyphType] | None = None,
) -> int:
    """Cast `letters` with `perk_id` in the slot of the glyph at `slot_at`;
    returns that glyph's final value."""
    types = types or [P] * len(letters)
    hand = [
        g(i, letter, type_, D if type_ == P else DEF, value)
        for i, (letter, type_) in enumerate(zip(letters, types, strict=True))
    ]
    state = match(*hand)
    state.players[0].hp = caster_hp
    state.players[1].hp = target_hp
    assert use(state, perk_id, f"p0-h{slot_at}").applied
    return resolve_word(state, 0, list(range(len(hand)))).steps[slot_at].final_value


class TestConditionalPerks:
    @pytest.mark.parametrize(
        ("perk_id", "letters", "slot_at", "expected"),
        [
            ("quick_jab", ["C", "A", "T"], 1, 22),
            ("quick_jab", ["C", "A", "T", "S"], 1, 8),
            ("twin_letters", ["B", "E", "E"], 0, 22),
            ("twin_letters", ["B", "E", "T"], 0, 8),
            ("twin_letters", ["T", "A", "T"], 0, 8),  # repeated, not side by side
            ("late_bloomer", ["C", "A", "T"], 2, 12),
            ("late_bloomer", ["C", "A", "T"], 1, 8),
            ("long_word", ["S", "T", "R", "I", "N", "G"], 0, 16),
            ("long_word", ["S", "T", "I", "N", "G"], 0, 8),
            ("lexicon", ["S", "T", "I", "N", "G"], 0, 14),
            ("lexicon", ["A", "T"], 0, 8),
            ("climber", ["S", "T", "I", "N", "G"], 4, 20),
            ("climber", ["S", "T", "R", "I", "N", "G", "S"], 6, 23),
            ("climber", ["S", "T"], 0, 8),
            ("grand_finale", ["S", "T", "I", "N", "G"], 4, 24),
            ("grand_finale", ["S", "T", "I", "N", "G"], 3, 8),
            ("grand_finale", ["S", "I", "N", "G"], 3, 8),
            ("matching_ends", ["T", "A", "T"], 0, 24),
            ("first_double", ["C", "A", "T"], 0, 16),
            ("last_double", ["C", "A", "T"], 2, 16),
            ("first_bonus", ["C", "A", "T"], 0, 17),
            ("last_bonus", ["C", "A", "T"], 2, 17),
            ("vowel_start", ["A", "T"], 1, 20),
            ("five_letters", ["S", "T", "I", "N", "G"], 2, 16),
        ],
    )
    def test_word_conditions(
        self, perk_id: str, letters: list[str], slot_at: int, expected: int
    ) -> None:
        assert cast(letters, slot_at, perk_id) == expected

    def test_onslaught_counts_power_glyphs(self) -> None:
        assert cast(["C", "A", "T"], 0, "onslaught", types=[P, S, P]) == 8 + 6
        assert cast(["C", "A", "T"], 0, "onslaught") == 8 + 9

    @pytest.mark.parametrize(
        ("caster_hp", "expected"),
        [(HP * 3 // 10, 16), (HP * 3 // 10 + 1, 8)],
    )
    def test_desperation(self, caster_hp: int, expected: int) -> None:
        assert cast(["C", "A", "T"], 0, "desperation", caster_hp=caster_hp) == expected

    @pytest.mark.parametrize(
        ("target_hp", "expected"),
        [(HP * 4 // 10, 24), (HP * 4 // 10 + 1, 8)],
    )
    def test_executioner(self, target_hp: int, expected: int) -> None:
        assert cast(["C", "A", "T"], 0, "executioner", target_hp=target_hp) == expected


def test_every_catalog_perk_is_tested_here() -> None:
    covered = {
        "sharpen", "round_up", "amplify", "overcharge", "blood", "fortify", "snowball",
        "double_or_halve", "ing", "er", "re", "ed", "pluralize", "qu", "vowel_shift",
        "consonant_shift", "wild_power", "wild_skill", "hex", "expose", "linger",
        "erase", "redraw", "fresh_start", "quick_jab", "twin_letters", "late_bloomer",
        "long_word", "lexicon", "climber", "grand_finale", "matching_ends",
        "first_double", "last_double", "first_bonus", "last_bonus", "vowel_start",
        "five_letters", "onslaught", "desperation", "executioner",
    }  # fmt: skip

    assert covered == set(load_catalog()) == set(registered())
