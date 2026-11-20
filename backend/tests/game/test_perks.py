"""Perks: the CSV catalog, the registered functions and the shared rules."""

import json

import pytest

pytest.importorskip("backend.game.perks", reason="Perks are not merged yet")

from backend.game.perks import (
    CatalogError,
    PerkError,
    PerkKind,
    PerkProblem,
    apply_perk,
    check_catalog,
    conditional_rules,
    grant_perk,
    load_catalog,
    registered,
)
from backend.game.perks.catalog import (
    COLUMNS,
    MAX_DESCRIPTION,
    MAX_NAME,
    parse_catalog,
)

from backend.game.config import Effect, GlyphType, Rarity
from backend.game.piles import new_match
from backend.game.resolution import Stage, resolve_word
from backend.game.state import Glyph, MatchState

P, S = GlyphType.POWER, GlyphType.SKILL
HEADER = ",".join(COLUMNS)
GOOD_ROW = "amplify,Amplify,rare,Double the value.,x2,,4,,power,ready"


def g(n: int, letters: str, type_: GlyphType = P, value: int = 8) -> Glyph:
    effect = Effect.DAMAGE if type_ == P else Effect.DEFENSE
    # "h" ids: the real deck in the draw pile already uses p0-g0...
    return Glyph(f"p0-h{n}", letters, type_, effect, value)


def match(*hand: Glyph, seed: str = "seed") -> MatchState:
    state = new_match("match-1", ("user-a", "user-b"), 180, seed=seed)
    state.players[0].hand = list(hand)
    return state


def use(state: MatchState, perk_id: str, glyph_id: str = "p0-h0"):  # type: ignore[no-untyped-def]
    instance = grant_perk(state, 0, perk_id)
    return apply_perk(state, 0, instance.instance_id, glyph_id)


class TestBundledCatalog:
    def test_every_row_has_a_function_and_every_function_a_row(self) -> None:
        check_catalog()
        assert set(load_catalog()) == set(registered())

    def test_rows_respect_the_sheet_limits(self) -> None:
        for spec in load_catalog().values():
            assert 1 <= len(spec.name) <= MAX_NAME
            assert 1 <= len(spec.description) <= MAX_DESCRIPTION
            assert spec.targets

    def test_known_rows(self) -> None:
        catalog = load_catalog()

        assert catalog["amplify"].rarity == Rarity.RARE
        assert catalog["amplify"].durability == 4
        assert catalog["erase"].targets == {S}
        assert catalog["matching_ends_x2"].targets == {P, S}
        assert catalog["last_plus_5"].durability is None

    def test_conditional_perks_are_registered_as_conditionals(self) -> None:
        definitions = registered()

        assert set(conditional_rules()) == {
            perk_id
            for perk_id, d in definitions.items()
            if d.kind == PerkKind.CONDITIONAL_SLOT
        }
        assert definitions["ing"].kind == PerkKind.LETTERS
        assert definitions["erase"].kind == PerkKind.DECK


class TestCheckCatalog:
    def test_row_without_function_is_reported(self) -> None:
        catalog = parse_catalog(
            f"{HEADER}\n{GOOD_ROW}\n" + GOOD_ROW.replace("amplify,", "mystery,", 1)
        )

        with pytest.raises(ValueError, match="no function: mystery"):
            check_catalog(catalog)

    def test_function_without_row_is_reported(self) -> None:
        catalog = parse_catalog(f"{HEADER}\n{GOOD_ROW}\n")

        with pytest.raises(ValueError, match="no catalog.csv row: .*double_or_halve"):
            check_catalog(catalog)


class TestParseCatalog:
    def test_reads_a_row(self) -> None:
        [spec] = parse_catalog(f"{HEADER}\n{GOOD_ROW}\n").values()

        assert spec.id == "amplify"
        assert spec.rarity == Rarity.RARE
        assert spec.durability == 4
        assert spec.targets == {P}
        assert spec.ready is True
        assert spec.quote is None and spec.image is None

    def test_both_targets_and_unlimited_durability(self) -> None:
        row = 'x2,X2,common,Desc.,,,,A quote,"skill, power",not_ready'

        [spec] = parse_catalog(f"{HEADER}\n{row}\n").values()

        assert spec.targets == {P, S}
        assert spec.durability is None
        assert spec.quote == "A quote"
        assert spec.ready is False

    @pytest.mark.parametrize(
        ("change", "message"),
        [
            (("amplify,", "Amp Lify,"), "id"),
            (("amplify,", ","), "id"),
            (("Amplify,", "A" * (MAX_NAME + 1) + ","), "name"),
            (("Amplify,", ","), "name"),
            (("Double the value.", "D" * (MAX_DESCRIPTION + 1)), "description"),
            ((",rare,", ",mythic,"), "rarity"),
            ((",4,", ",0,"), "durability"),
            ((",4,", ",four,"), "durability"),
            ((",power,", ",magic,"), "target_type"),
            ((",power,", ",,"), "target_type"),
            ((",ready", ",maybe"), "status"),
        ],
    )
    def test_bad_rows_name_the_line_and_problem(
        self, change: tuple[str, str], message: str
    ) -> None:
        row = GOOD_ROW.replace(*change, 1)

        with pytest.raises(CatalogError, match=f"line 2: {message}"):
            parse_catalog(f"{HEADER}\n{row}\n")

    def test_duplicate_id(self) -> None:
        with pytest.raises(CatalogError, match="line 3: id amplify appears twice"):
            parse_catalog(f"{HEADER}\n{GOOD_ROW}\n{GOOD_ROW}\n")

    def test_wrong_columns(self) -> None:
        with pytest.raises(CatalogError, match="columns"):
            parse_catalog("id,name\namplify,Amplify\n")


class TestDirectPerks:
    def test_amplify_doubles(self) -> None:
        state = match(g(0, "B", value=20))

        result = use(state, "amplify")

        assert result.applied is True
        assert state.players[0].hand[0].value == 40

    @pytest.mark.parametrize(
        ("perk_id", "letters", "bonus"),
        [("ing", "ING", 7), ("er", "ER", 5), ("re", "RE", 5)],
    )
    def test_letter_perks_transform_and_raise_value(
        self, perk_id: str, letters: str, bonus: int
    ) -> None:
        state = match(g(0, "S", value=8))

        use(state, perk_id)

        glyph = state.players[0].hand[0]
        assert (glyph.letters, glyph.value) == (letters, 8 + bonus)

    def test_letter_perk_on_same_letters_does_nothing_and_keeps_durability(
        self,
    ) -> None:
        state = match(g(0, "ING", value=8))

        result = use(state, "ing")

        assert result.applied is False
        assert result.durability_left == 4
        assert (state.players[0].hand[0].letters, state.players[0].hand[0].value) == (
            "ING",
            8,
        )

    def test_letter_perk_replaces_other_letters(self) -> None:
        state = match(g(0, "ER", value=13))

        use(state, "ing")

        assert (state.players[0].hand[0].letters, state.players[0].hand[0].value) == (
            "ING",
            20,
        )

    def test_erase_removes_the_glyph_from_the_match(self) -> None:
        state = match(g(0, "R", S), g(1, "S"))
        before = len(state.players[0].all_glyphs())

        result = use(state, "erase")

        assert result.applied is True
        assert result.glyph is None
        assert [x.id for x in state.players[0].hand] == ["p0-h1"]
        assert len(state.players[0].all_glyphs()) == before - 1

    def test_double_or_halve_is_seeded(self) -> None:
        outcomes = []
        for seed in ("a", "a", "b", "c", "d", "e", "f", "g", "h"):
            state = match(g(0, "S", value=9), seed=seed)
            use(state, "double_or_halve")
            outcomes.append(state.players[0].hand[0].value)

        assert outcomes[0] == outcomes[1]
        assert set(outcomes) == {18, 4}

    def test_each_use_draws_again(self) -> None:
        # The draw depends on the use (durability left), so one perk doesn't
        # always double or always halve.
        mixed = False
        for seed in ("s1", "s2", "s3", "s4", "s5"):
            state = match(g(0, "S", value=1024), seed=seed)
            instance = grant_perk(state, 0, "double_or_halve")
            doubled = set()
            for _ in range(4):
                before = state.players[0].hand[0].value
                apply_perk(state, 0, instance.instance_id, "p0-h0")
                doubled.add(state.players[0].hand[0].value > before)
            mixed |= len(doubled) == 2

        assert mixed


class TestSharedRules:
    def test_wrong_target_type_is_rejected_unchanged(self) -> None:
        state = match(g(0, "R", S, value=15))
        instance = grant_perk(state, 0, "amplify")
        before = state.to_dict()

        with pytest.raises(PerkError) as caught:
            apply_perk(state, 0, instance.instance_id, "p0-h0")

        assert caught.value.problem == PerkProblem.WRONG_TARGET
        assert state.to_dict() == before

    def test_unknown_instance(self) -> None:
        state = match(g(0, "S"))

        with pytest.raises(PerkError) as caught:
            apply_perk(state, 0, "p0-k99", "p0-h0")

        assert caught.value.problem == PerkProblem.UNKNOWN_INSTANCE

    def test_other_players_perk_is_not_yours(self) -> None:
        state = match(g(0, "S"))
        theirs = grant_perk(state, 1, "amplify")

        with pytest.raises(PerkError) as caught:
            apply_perk(state, 0, theirs.instance_id, "p0-h0")

        assert caught.value.problem == PerkProblem.UNKNOWN_INSTANCE

    def test_glyph_must_be_in_hand(self) -> None:
        state = match(g(0, "S"))
        instance = grant_perk(state, 0, "amplify")
        draw_glyph = state.players[0].draw_pile[-1]
        before = state.to_dict()

        with pytest.raises(PerkError) as caught:
            apply_perk(state, 0, instance.instance_id, draw_glyph.id)

        assert caught.value.problem == PerkProblem.GLYPH_NOT_IN_HAND
        assert state.to_dict() == before

    def test_perk_missing_from_catalog(self) -> None:
        state = match(g(0, "S"))
        with pytest.raises(PerkError) as caught:
            grant_perk(state, 0, "no_such_perk")
        assert caught.value.problem == PerkProblem.UNKNOWN_PERK

    def test_durability_drops_and_perk_breaks_at_zero(self) -> None:
        state = match(g(0, "S", value=1))
        instance = grant_perk(state, 0, "amplify")
        assert instance.durability == 4

        left = [apply_perk(state, 0, instance.instance_id, "p0-h0") for _ in range(4)]

        assert [r.durability_left for r in left] == [3, 2, 1, 0]
        assert [r.destroyed for r in left] == [False, False, False, True]
        assert state.players[0].perks == []
        assert state.players[0].hand[0].value == 16
        with pytest.raises(PerkError):
            apply_perk(state, 0, instance.instance_id, "p0-h0")

    def test_unlimited_durability_never_breaks(self) -> None:
        state = match(g(0, "S"), g(1, "T"))
        instance = grant_perk(state, 0, "last_plus_5")

        for glyph_id in ("p0-h0", "p0-h1") * 5:
            result = apply_perk(state, 0, instance.instance_id, glyph_id)
            assert result.durability_left is None

        assert state.players[0].perks == [instance]

    def test_grant_gives_unique_instance_ids(self) -> None:
        state = match(g(0, "S", value=1))
        ids = []
        for _ in range(3):
            instance = grant_perk(state, 0, "amplify")
            ids.append(instance.instance_id)
        # Break one, then grant again: the new id must not clash.
        for _ in range(4):
            apply_perk(state, 0, ids[0], "p0-h0")
        ids.append(grant_perk(state, 0, "amplify").instance_id)

        assert len(set(ids)) == 4
        assert len({p.instance_id for p in state.players[0].perks}) == 3


class TestConditionalPerks:
    def test_fills_the_slot(self) -> None:
        state = match(g(0, "S"))

        result = use(state, "last_plus_5")

        assert result.applied is True
        assert state.players[0].hand[0].conditional_slot == "last_plus_5"

    def test_same_conditional_again_does_nothing(self) -> None:
        state = match(g(0, "S"))
        use(state, "last_plus_5")

        result = use(state, "last_plus_5")

        assert result.applied is False

    def test_new_conditional_replaces_the_old(self) -> None:
        state = match(g(0, "S"))
        use(state, "last_plus_5")

        result = use(state, "first_plus_5")

        assert result.applied is True
        assert state.players[0].hand[0].conditional_slot == "first_plus_5"

    def test_does_not_change_the_value_until_the_word_resolves(self) -> None:
        state = match(g(0, "S", value=8))

        use(state, "first_times_2")

        assert state.players[0].hand[0].value == 8

    @pytest.mark.parametrize(
        ("perk_id", "letters", "slot_at", "expected"),
        [
            ("last_plus_5", ["C", "A", "T"], 2, 13),
            ("last_plus_5", ["C", "A", "T"], 0, 8),
            ("first_plus_5", ["C", "A", "T"], 0, 13),
            ("first_plus_5", ["C", "A", "T"], 1, 8),
            ("last_times_2", ["C", "A", "T"], 2, 16),
            ("last_times_2", ["C", "A", "T"], 1, 8),
            ("first_times_2", ["C", "A", "T"], 0, 16),
            ("first_times_2", ["C", "A", "T"], 2, 8),
            ("vowel_start_plus_10", ["A", "C", "T"], 2, 18),
            ("vowel_start_plus_10", ["C", "A", "T"], 2, 8),
            ("five_letters_plus_8", ["S", "ING", "S"], 0, 16),
            ("five_letters_plus_8", ["S", "ING"], 0, 8),
            ("matching_ends_x2", ["T", "A", "T"], 1, 16),
            ("matching_ends_x2", ["C", "A", "T"], 1, 8),
        ],
    )
    def test_rules_at_resolution(
        self, perk_id: str, letters: list[str], slot_at: int, expected: int
    ) -> None:
        hand = [g(i, letter, value=8) for i, letter in enumerate(letters)]
        state = match(*hand)
        use(state, perk_id, f"p0-h{slot_at}")

        result = resolve_word(state, 0, list(range(len(hand))))

        step = result.steps[slot_at]
        assert step.final_value == expected
        if expected != 8:
            [change] = step.changes
            assert (change.stage, change.perk_id) == (Stage.CONDITIONAL, perk_id)


class TestPayload:
    def test_is_json_safe(self) -> None:
        state = match(g(0, "S", value=8))

        payload = json.loads(json.dumps(use(state, "ing").to_dict()))

        assert payload == {
            "player": 0,
            "instance_id": "p0-k0",
            "perk_id": "ing",
            "glyph_id": "p0-h0",
            "applied": True,
            "durability_left": 3,
            "destroyed": False,
            "glyph": {
                "id": "p0-h0",
                "letters": "ING",
                "type": "POWER",
                "effect": "DAMAGE",
                "value": 15,
                "conditional_slot": None,
            },
        }

    def test_erased_glyph_is_null(self) -> None:
        state = match(g(0, "R", S))
        assert use(state, "erase").to_dict()["glyph"] is None
