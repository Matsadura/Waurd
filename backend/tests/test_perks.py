"""Perks: the CSV catalog and its sync, drafting, applying, durability, bonus
slots, every perk function, loadouts, the STATE and the socket messages."""

import random
import uuid
from collections import Counter

import pytest

perks_pkg = pytest.importorskip("backend.game.perks", reason="perks not merged yet")

from sqlalchemy import select
from starlette.testclient import TestClient

from backend.game.models import Glyph, Match
from backend.game.perks import play
from backend.game.perks.catalog import CATALOG, load_catalog
from backend.game.perks.effects import BONUS, DIRECT, KIND, WordContext
from backend.game.rules import (
    STARTING_HP,
    apply_perk,
    cast_word,
    pass_turn,
    reroll_perks,
    select_perks,
    start_turn,
)
from backend.game.setup import new_match
from backend.main import app
from backend.models import Match as MatchRecord
from backend.models import MatchStatus, Perk
from backend.models.user_loadout import UserLoadout
from backend.ws import match_ws, records

ORIGIN = "http://localhost:5173"


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch, session_maker):  # type: ignore[no-untyped-def]
    match_ws.matches.clear()
    match_ws.sockets.clear()
    match_ws.timers.clear()
    match_ws.clocks.clear()
    monkeypatch.setattr(records, "async_session_maker", session_maker)
    yield
    for task in [*match_ws.timers.values(), *match_ws.clocks.values()]:
        task.cancel()


def game(loadout=()):  # type: ignore[no-untyped-def]
    """alice (seat 0) to move on turn 1 with an empty hand to fill, holding `loadout`."""
    g = new_match(seed=1, loadouts=(list(loadout), []))
    g.names = ("alice", "bob")
    g.active_player_index = 0
    start_turn(g)
    g.players[0].hand = []
    return g


def hit(letter="T", value=10):  # type: ignore[no-untyped-def]
    return Glyph(letter, value)


def holding(g: Match, perk_id: str) -> int:
    """Give alice a fresh copy of a perk; returns its instance id."""
    return play.grant(g, 0, perk_id).id


# Catalog --------------------------------------------------------------------


class TestCatalog:
    def test_has_the_41_perks_from_the_sheet(self) -> None:
        assert len(CATALOG) == 41
        assert {"sharpen", "overcharge", "grand_finale"} <= set(CATALOG)

    def test_every_row_has_exactly_one_function(self) -> None:
        assert set(DIRECT) | set(BONUS) == set(CATALOG)
        assert not set(DIRECT) & set(BONUS)
        assert set(KIND) == set(CATALOG)

    def test_targets_follow_the_descriptions(self) -> None:
        assert CATALOG["sharpen"].target == "damage"
        assert CATALOG["fortify"].target == "heal_defense"  # "Defense or Heal glyph"
        assert CATALOG["hex"].target == "any"

    def test_rows_are_read_with_their_types(self) -> None:
        overcharge = CATALOG["overcharge"]
        assert (overcharge.rarity, overcharge.durability, overcharge.ready) == (
            "legendary",
            1,
            True,
        )

    @pytest.mark.parametrize(
        ("column", "value", "problem"),
        [
            ("id", "Bad Id", "id"),
            ("rarity", "mythic", "rarity"),
            ("target_type", "power", "target_type"),
            ("durability", "0", "durability"),
            ("status", "maybe", "status"),
        ],
    )
    def test_a_bad_row_names_the_line(self, tmp_path, column, value, problem) -> None:
        row = {
            "id": "x",
            "name": "X",
            "rarity": "common",
            "description": "d",
            "mechanics": "m",
            "image": "",
            "durability": "2",
            "quote": "",
            "target_type": "any",
            "status": "ready",
        }
        row[column] = value
        path = tmp_path / "catalog.csv"
        path.write_text(",".join(row) + "\n" + ",".join(row.values()) + "\n")

        with pytest.raises(ValueError, match=f"line 2: {problem}"):
            load_catalog(path)

    def test_an_empty_durability_never_breaks(self, tmp_path) -> None:
        path = tmp_path / "catalog.csv"
        path.write_text(
            "id,name,rarity,description,mechanics,image,durability,quote,target_type,status\n"
            "x,X,common,d,m,,,,any,not_ready\n"
        )

        spec = load_catalog(path)["x"]

        assert (spec.durability, spec.ready) == (None, False)


class TestSyncPerks:
    async def test_fills_the_perks_table_from_the_csv(self, session_maker) -> None:
        await records.sync_perks()

        async with session_maker() as db:
            rows = {p.id: p for p in await db.scalars(select(Perk))}
        assert len(rows) == 41
        fortify = rows["fortify"]
        assert (fortify.target_glyph_type.value, fortify.modification_type.value) == (
            "HEAL_DEFENSE",
            "POWER_VALUE",
        )
        assert rows["last_bonus"].modification_type.value == "CONDITIONAL_SLOT"
        assert rows["sharpen"].effect_payload == {"mechanics": "value += 4"}
        assert all(row.is_enabled for row in rows.values())

    async def test_updates_rows_and_disables_ones_no_longer_listed(
        self, session_maker
    ) -> None:
        await records.sync_perks()
        async with session_maker() as db:
            (await db.get(Perk, "sharpen")).name = "Old name"
            db.add(
                Perk(
                    id="retired",
                    name="Retired",
                    description="gone",
                    rarity="COMMON",
                    target_glyph_type="ANY",
                    modification_type="DECK",
                    effect_payload={},
                    is_enabled=True,
                )
            )
            await db.commit()

        await records.sync_perks()

        async with session_maker() as db:
            assert (await db.get(Perk, "sharpen")).name == "Sharpen"
            assert (await db.get(Perk, "retired")).is_enabled is False


# Draft ----------------------------------------------------------------------


class TestDraft:
    def test_a_cast_offers_three_different_ready_perks(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]

        cast_word(g, 0, [0, 1], {"AT"})

        draft = g.players[0].draft
        assert len(draft) == len(set(draft)) == 3
        assert all(CATALOG[p].ready for p in draft)
        assert g.active_player_index == 0  # still alice's turn until she picks

    def test_casting_again_before_picking_is_rejected(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1), hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})

        with pytest.raises(ValueError, match="pick a perk or skip"):
            cast_word(g, 0, [0, 1], {"AT"})

    def test_picking_grants_the_perk_and_ends_the_turn(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})
        chosen = g.players[0].draft[0]

        select_perks(g, 0, [chosen])

        (instance,) = g.players[0].perks
        assert (instance.perk_id, instance.durability) == (
            chosen,
            CATALOG[chosen].durability,
        )
        assert g.players[0].draft == []
        assert g.active_player_index == 1
        assert g.log[-1] == f"alice took {CATALOG[chosen].name}"

    def test_skipping_ends_the_turn_without_a_perk(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})

        select_perks(g, 0, [])

        assert g.players[0].perks == []
        assert g.active_player_index == 1

    def test_passing_after_a_cast_skips_the_draft(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})

        pass_turn(g, 0)

        assert (g.players[0].draft, g.active_player_index) == ([], 1)

    @pytest.mark.parametrize(
        ("picks", "problem"),
        [
            (["not_offered"], "wasn't offered"),
            (["sharpen", "amplify"], "Pick one perk"),
            ("sharpen", "Pick one perk"),
        ],
    )
    def test_bad_picks_are_rejected(self, picks, problem) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})
        g.players[0].draft = ["first_bonus", "hex", "erase"]

        with pytest.raises(ValueError, match=problem):
            select_perks(g, 0, picks)

    def test_picking_without_a_draft_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="no perk draft"):
            select_perks(game(), 0, ["sharpen"])

    def test_rerolling_swaps_the_offer_and_uses_a_reroll(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})
        before = list(g.players[0].draft)

        reroll_perks(g, 0)

        assert g.players[0].rerolls_left == play.REROLLS_PER_MATCH - 1
        assert len(g.players[0].draft) == 3
        assert g.players[0].draft != before or len(CATALOG) <= 3
        assert g.log[-1] == "alice rerolled the perk draft"

    def test_rerolls_run_out(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})
        g.players[0].rerolls_left = 0

        with pytest.raises(ValueError, match="No rerolls left"):
            reroll_perks(g, 0)

    def test_the_other_player_cannot_pick(self) -> None:
        g = game()
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        cast_word(g, 0, [0, 1], {"AT"})

        with pytest.raises(ValueError, match="not your turn"):
            select_perks(g, 1, [])

    def test_a_winning_cast_offers_nothing(self) -> None:
        g = game()
        g.players[1].hp = 1
        g.players[1].defense = 0
        g.players[0].hand = [hit("A", 5), hit("T", 5)]

        cast_word(g, 0, [0, 1], {"AT"})

        assert (g.winner, g.players[0].draft) == (0, [])

    def test_rarer_perks_are_offered_less_often(self) -> None:
        g = game()
        g.rng = random.Random(7)
        seen = Counter(CATALOG[p].rarity for _ in range(600) for p in play.offer(g))
        per_perk = {
            rarity: seen[rarity] / sum(s.rarity == rarity for s in CATALOG.values())
            for rarity in ("common", "legendary")
        }

        assert per_perk["common"] > 3 * per_perk["legendary"]


# Applying -------------------------------------------------------------------


class TestApply:
    def test_spends_one_durability_and_breaks_at_zero(self) -> None:
        g = game()
        instance = holding(g, "overcharge")  # durability 1
        g.players[0].hand = [hit(value=10)]

        apply_perk(g, 0, instance, 0)

        assert g.players[0].hand[0].effect_value == 25
        assert g.players[0].perks == []
        assert g.log[-2:] == ["alice used Overcharge on T", "alice's Overcharge broke"]

    def test_durability_counts_down(self) -> None:
        g = game()
        instance = holding(g, "sharpen")  # durability 4
        g.players[0].hand = [hit(value=10)]

        apply_perk(g, 0, instance, 0)
        apply_perk(g, 0, instance, 0)

        assert g.players[0].perks[0].durability == 2
        assert g.players[0].hand[0].effect_value == 18

    def test_a_perk_with_no_effect_keeps_its_durability(self) -> None:
        g = game()
        instance = holding(g, "ing")
        g.players[0].hand = [hit("ING", 10)]

        apply_perk(g, 0, instance, 0)

        assert g.players[0].perks[0].durability == CATALOG["ing"].durability
        assert g.log[-1] == "alice's -ING- had no effect"

    @pytest.mark.parametrize(
        ("perk_id", "glyph"),
        [
            ("sharpen", Glyph("A", 9, "power", "heal")),  # damage only
            ("fortify", Glyph("T", 9)),  # heal or defense only
        ],
    )
    def test_the_wrong_target_is_rejected(self, perk_id, glyph) -> None:
        g = game()
        instance = holding(g, perk_id)
        g.players[0].hand = [glyph]

        with pytest.raises(ValueError, match="can't go on"):
            apply_perk(g, 0, instance, 0)

    def test_rejected_after_casting(self) -> None:
        g = game()
        instance = holding(g, "sharpen")
        g.players[0].hand = [hit("A", 1), hit("T", 1), hit()]
        cast_word(g, 0, [0, 1], {"AT"})

        with pytest.raises(ValueError, match="already cast"):
            apply_perk(g, 0, instance, 0)

    @pytest.mark.parametrize(
        ("instance_id", "position", "player", "problem"),
        [
            (999, 0, 0, "don't have that perk"),
            ("1", 0, 0, "don't have that perk"),
            (None, 5, 0, "out of bounds"),
            (None, 0, 1, "not your turn"),
        ],
    )
    def test_bad_requests_are_rejected(
        self, instance_id, position, player, problem
    ) -> None:
        g = game()
        instance = holding(g, "sharpen")
        g.players[0].hand = [hit()]

        with pytest.raises(ValueError, match=problem):
            apply_perk(
                g, player, instance if instance_id is None else instance_id, position
            )


class TestBonusSlot:
    def test_fills_the_slot_and_counts_when_cast(self) -> None:
        g = game()
        instance = holding(g, "last_bonus")
        g.players[0].hand = [hit("A", 5), hit("T", 5)]
        apply_perk(g, 0, instance, 1)
        g.players[1].defense = 0

        cast_word(g, 0, [0, 1], {"AT"})

        assert g.players[1].hp == STARTING_HP - (5 + 5 + 9)

    def test_does_nothing_when_its_condition_fails(self) -> None:
        g = game()
        instance = holding(g, "last_bonus")
        g.players[0].hand = [hit("A", 5), hit("T", 5)]
        apply_perk(g, 0, instance, 0)  # A is first, not last
        g.players[1].defense = 0

        cast_word(g, 0, [0, 1], {"AT"})

        assert g.players[1].hp == STARTING_HP - 10

    def test_counts_before_weak(self) -> None:
        g = game()
        instance = holding(g, "first_bonus")
        g.players[0].hand = [hit("T", 11)]
        g.players[0].statuses = {"weak": 1}
        apply_perk(g, 0, instance, 0)
        g.players[1].defense = 0

        cast_word(g, 0, [0], {"T"})

        assert g.players[1].hp == STARTING_HP - (11 + 9) * 75 // 100

    def test_the_same_bonus_twice_has_no_effect(self) -> None:
        g = game()
        first, second = holding(g, "last_bonus"), holding(g, "last_bonus")
        g.players[0].hand = [hit()]
        apply_perk(g, 0, first, 0)

        apply_perk(g, 0, second, 0)

        assert [p.durability for p in g.players[0].perks] == [2, 3]

    def test_a_new_bonus_replaces_the_old_one(self) -> None:
        g = game()
        g.players[0].hand = [hit()]
        apply_perk(g, 0, holding(g, "last_bonus"), 0)

        apply_perk(g, 0, holding(g, "first_bonus"), 0)

        assert g.players[0].hand[0].bonus == "first_bonus"

    def test_weak_and_vulnerable_glyphs_take_no_bonus(self) -> None:
        g = game()
        instance = holding(g, "last_double")  # any glyph
        g.players[0].hand = [Glyph("V", 2, "skill", "vulnerable")]

        apply_perk(g, 0, instance, 0)

        assert g.players[0].hand[0].bonus is None
        assert g.players[0].perks[0].durability == CATALOG["last_double"].durability


# Every perk function --------------------------------------------------------


@pytest.mark.parametrize(
    ("perk_id", "before", "after"),
    [
        ("sharpen", 10, 14),
        ("round_up", 10, 15),
        ("round_up", 12, 15),
        ("amplify", 11, 16),
        ("overcharge", 11, 27),
        ("snowball", 10, 13),
    ],
)
def test_value_perks(perk_id, before, after) -> None:  # type: ignore[no-untyped-def]
    g = game()
    g.players[0].hand = [hit(value=before)]

    apply_perk(g, 0, holding(g, perk_id), 0)

    assert g.players[0].hand[0].effect_value == after


def test_fortify_raises_a_heal_glyph() -> None:
    g = game()
    g.players[0].hand = [Glyph("A", 9, "power", "heal")]

    apply_perk(g, 0, holding(g, "fortify"), 0)

    assert g.players[0].hand[0].effect_value == 15


def test_snowball_grows_with_each_use() -> None:
    g = game()
    g.players[0].hand = [hit(value=0)]
    instance = holding(g, "snowball")

    for _ in range(3):
        apply_perk(g, 0, instance, 0)

    assert g.players[0].hand[0].effect_value == 3 + 6 + 9


def test_double_or_halve_does_one_or_the_other() -> None:
    results = set()
    for seed in range(20):
        g = game()
        g.rng = random.Random(seed)
        g.players[0].hand = [hit(value=10)]
        apply_perk(g, 0, holding(g, "double_or_halve"), 0)
        results.add(g.players[0].hand[0].effect_value)

    assert results == {20, 5}


def test_blood_costs_hp_but_never_the_last_one() -> None:
    g = game()
    g.players[0].hand = [hit(value=10), hit(value=10)]
    g.players[0].hp = 12
    instance = holding(g, "blood")

    apply_perk(g, 0, instance, 0)
    apply_perk(g, 0, instance, 1)

    assert [glyph.effect_value for glyph in g.players[0].hand] == [25, 25]
    assert g.players[0].hp == 1


@pytest.mark.parametrize(
    ("perk_id", "letters", "raise_by"),
    [
        ("ing", "ING", 7),
        ("er", "ER", 5),
        ("re", "RE", 5),
        ("ed", "ED", 5),
        ("pluralize", "S", 3),
        ("qu", "QU", 18),
    ],
)
def test_letter_perks(perk_id, letters, raise_by) -> None:  # type: ignore[no-untyped-def]
    g = game()
    g.players[0].hand = [hit("T", 10)]

    apply_perk(g, 0, holding(g, perk_id), 0)

    assert (g.players[0].hand[0].letter, g.players[0].hand[0].effect_value) == (
        letters,
        10 + raise_by,
    )


def test_a_transformed_glyph_spells_its_letters() -> None:
    g = game()
    g.players[0].hand = [hit("S", 1), hit("T", 1)]
    apply_perk(g, 0, holding(g, "ing"), 1)

    cast_word(g, 0, [0, 1], {"SING"})

    assert g.casts[-1].word == "SING"


@pytest.mark.parametrize(
    ("perk_id", "letters", "raise_by"),
    [("vowel_shift", "AEIOU", 2), ("consonant_shift", "STNRLD", 4)],
)
def test_shifts_pick_a_different_letter(perk_id, letters, raise_by) -> None:  # type: ignore[no-untyped-def]
    g = game()
    g.players[0].hand = [hit(letters[0], 10)]

    apply_perk(g, 0, holding(g, perk_id), 0)

    glyph = g.players[0].hand[0]
    assert glyph.letter in letters and glyph.letter != letters[0]
    assert glyph.effect_value == 10 + raise_by


def test_a_shift_on_a_status_glyph_keeps_its_turns() -> None:
    g = game()
    g.players[0].hand = [Glyph("E", 2, "skill", "weak")]

    apply_perk(g, 0, holding(g, "vowel_shift"), 0)

    assert g.players[0].hand[0].effect_value == 2


def test_wild_power_turns_heal_into_damage() -> None:
    g = game()
    g.players[0].hand = [Glyph("A", 9, "power", "heal")]

    apply_perk(g, 0, holding(g, "wild_power"), 0)

    glyph = g.players[0].hand[0]
    assert (glyph.effect_type, glyph.effect_value) == ("damage", 13)


def test_wild_skill_turns_damage_into_heal_or_defense() -> None:
    g = game()
    g.players[0].hand = [hit(value=10)]

    apply_perk(g, 0, holding(g, "wild_skill"), 0)

    glyph = g.players[0].hand[0]
    assert glyph.effect_type in ("heal", "defense")
    assert glyph.effect_value == 16


@pytest.mark.parametrize(
    ("perk_id", "before", "after"),
    [
        ("hex", {}, {"weak": 3}),
        ("expose", {}, {"vulnerable": 3}),
        ("linger", {}, {"weak": 2}),
        ("linger", {"weak": 1, "vulnerable": 2}, {"weak": 3, "vulnerable": 4}),
        ("hex", {"weak": 5}, {"weak": 5}),  # the longer time is kept
    ],
)
def test_status_perks_hit_the_opponent(perk_id, before, after) -> None:  # type: ignore[no-untyped-def]
    g = game()
    g.players[1].statuses = dict(before)
    g.players[0].hand = [hit()]

    apply_perk(g, 0, holding(g, perk_id), 0)

    assert g.players[1].statuses == after
    assert g.players[0].hand[0].effect_value == 10  # the glyph is unchanged


def test_expose_already_counts_for_this_turns_word() -> None:
    g = game()
    g.players[1].defense = 0
    g.players[0].hand = [hit("T", 10)]
    apply_perk(g, 0, holding(g, "expose"), 0)

    cast_word(g, 0, [0], {"T"})

    assert g.players[1].hp == STARTING_HP - 15


def _every_glyph(player) -> list:  # type: ignore[no-untyped-def]
    return [*player.hand, *player.draw_pile, *player.discard_pile]


def test_erase_removes_the_glyph_from_the_match_and_draws() -> None:
    g = game()
    erased = hit("Z", 1)
    g.players[0].hand = [erased, hit()]
    total = len(_every_glyph(g.players[0]))

    apply_perk(g, 0, holding(g, "erase"), 0)

    assert len(g.players[0].hand) == 2
    assert not any(glyph is erased for glyph in _every_glyph(g.players[0]))
    assert len(_every_glyph(g.players[0])) == total - 1


def test_redraw_discards_and_draws_a_stronger_glyph() -> None:
    g = game()
    old = hit("Z", 1)
    g.players[0].hand = [old]
    g.players[0].draw_pile = [hit("K", 10)]

    apply_perk(g, 0, holding(g, "redraw"), 0)

    assert g.players[0].discard_pile[-1] is old
    assert [(x.letter, x.effect_value) for x in g.players[0].hand] == [("K", 15)]


def test_fresh_start_replaces_the_hand_with_stronger_glyphs() -> None:
    g = game()
    g.players[0].hand = [hit("A", 1), hit("B", 1)]
    g.players[0].draw_pile = [
        hit("C", 10),
        hit("D", 10),
        Glyph("E", 2, "skill", "weak"),
    ]

    apply_perk(g, 0, holding(g, "fresh_start"), 0)

    assert sorted((x.letter, x.effect_value) for x in g.players[0].hand) == [
        ("D", 13),
        ("E", 2),  # a status glyph keeps its turns
    ]
    assert len(g.players[0].discard_pile) >= 2


def word(text, index, caster_hp=100, target_hp=100):  # type: ignore[no-untyped-def]
    glyphs = [hit(c, 10) for c in text]
    return WordContext(text, glyphs, index, caster_hp, target_hp, STARTING_HP)


@pytest.mark.parametrize(
    ("perk_id", "where", "value"),
    [
        ("last_bonus", word("CAT", 2), 19),
        ("last_bonus", word("CAT", 1), 10),
        ("first_bonus", word("CAT", 0), 19),
        ("last_double", word("CAT", 2), 20),
        ("first_double", word("CAT", 0), 20),
        ("first_double", word("CAT", 1), 10),
        ("vowel_start", word("OAT", 1), 22),
        ("vowel_start", word("CAT", 1), 10),
        ("five_letters", word("TOAST", 0), 18),
        ("five_letters", word("TOAD", 0), 10),
        ("matching_ends", word("TOT", 1), 30),
        ("matching_ends", word("TOP", 1), 10),
        ("quick_jab", word("CAT", 0), 24),
        ("quick_jab", word("CATS", 0), 10),
        ("twin_letters", word("BELL", 0), 24),
        ("twin_letters", word("BELT", 0), 10),
        ("late_bloomer", word("CATS", 2), 15),
        ("late_bloomer", word("CATS", 1), 10),
        ("long_word", word("CASTLE", 0), 20),
        ("long_word", word("CASTS", 0), 10),
        ("onslaught", word("CAT", 0), 19),  # three damage glyphs
        ("lexicon", word("CASTLE", 0), 18),
        ("climber", word("CASTLES", 6), 25),  # capped at +15
        ("climber", word("CAT", 1), 13),
        ("desperation", word("CAT", 0, caster_hp=30), 20),
        ("desperation", word("CAT", 0, caster_hp=31), 10),
        ("executioner", word("CAT", 0, target_hp=40), 30),
        ("executioner", word("CAT", 0, target_hp=41), 10),
        ("grand_finale", word("TOAST", 4), 30),
        ("grand_finale", word("TOAD", 3), 10),
    ],
)
def test_bonus_perks(perk_id, where, value) -> None:  # type: ignore[no-untyped-def]
    assert BONUS[perk_id](where.glyphs[where.index], where, 10) == value


# Loadouts, STATE and the socket ---------------------------------------------


def test_loadout_perks_start_in_hand() -> None:
    g = new_match(seed=1, loadouts=(["sharpen", "hex"], ["amplify"]))

    assert [p.perk_id for p in g.players[0].perks] == ["sharpen", "hex"]
    assert [p.perk_id for p in g.players[1].perks] == ["amplify"]
    assert len({p.id for side in g.players for p in side.perks}) == 3
    assert all(side.rerolls_left == play.REROLLS_PER_MATCH for side in g.players)


async def test_match_setup_reads_the_equipped_perks(session_maker, alice, bob) -> None:
    await records.sync_perks()
    match_id = uuid.uuid4()
    async with session_maker() as db:
        db.add(
            MatchRecord(
                id=match_id.bytes,
                player1_id=alice.id,
                player2_id=bob.id,
                time_control_seconds=180,
                status=MatchStatus.ACTIVE,
            )
        )
        db.add(UserLoadout(user_id=alice.id, perk_id="sharpen"))
        await db.commit()

    seconds, names, loadouts = await records.match_setup(str(match_id))

    assert (seconds, names, loadouts) == (180, ("alice", "bob"), (["sharpen"], []))


def test_the_state_shows_perks_the_draft_and_bonus_slots() -> None:
    g = game(loadout=["last_bonus"])
    g.players[0].hand = [hit("A", 1), hit("T", 1)]
    apply_perk(g, 0, g.players[0].perks[0].id, 1)
    cast_word(g, 0, [0], {"A"})

    mine, theirs = match_ws.view(g, 0), match_ws.view(g, 1)

    (perk,) = mine["you"]["perks"]
    assert perk["perk_id"] == "last_bonus"
    assert perk["durability_left"] == CATALOG["last_bonus"].durability - 1
    assert set(perk) == {
        "instance_id",
        "perk_id",
        "name",
        "rarity",
        "description",
        "target",
        "durability",
        "durability_left",
    }
    assert [o["perk_id"] for o in mine["you"]["draft"]["options"]] == g.players[0].draft
    assert mine["you"]["draft"]["rerolls_left"] == play.REROLLS_PER_MATCH
    assert mine["you"]["hand"][1]["bonus"] == "last_bonus"
    assert theirs["you"]["draft"] is None
    assert theirs["opponent"]["perk_count"] == 1


@pytest.fixture
def client(monkeypatch):  # type: ignore[no-untyped-def]
    async def user(ws):  # type: ignore[no-untyped-def]
        return ws.headers.get("x-user")

    async def seat(match_id, user_id):  # type: ignore[no-untyped-def]
        return {"a": 0, "b": 1}.get(user_id)

    async def setup(match_id):  # type: ignore[no-untyped-def]
        return 300, ("a", "b"), (["sharpen"], [])

    async def end(app, match_id, game):  # type: ignore[no-untyped-def]
        match_ws.matches.pop(match_id, None)

    monkeypatch.setattr(match_ws, "user_id_from_cookie", user)
    monkeypatch.setattr(match_ws, "seat_in_match", seat)
    monkeypatch.setattr(match_ws, "match_setup", setup)
    monkeypatch.setattr(match_ws, "end_match", end)
    monkeypatch.setattr(match_ws.settings, "CORS_ORIGINS", [ORIGIN])
    return TestClient(app)


def test_perk_messages_over_the_socket(client) -> None:  # type: ignore[no-untyped-def]
    match_id = str(uuid.uuid4())
    connect = lambda who: client.websocket_connect(  # noqa: E731
        f"/ws/matches/{match_id}", headers={"origin": ORIGIN, "x-user": who}
    )
    with connect("a") as a, connect("b") as b:
        a.receive_json()
        a.receive_json()
        b.receive_json()
        g = match_ws.matches[match_id]
        g.active_player_index = 0
        g.players[0].hand = [hit("A", 1), hit("T", 1)]
        sharpen_id = g.players[0].perks[0].id

        a.send_json({"type": "APPLY_PERK", "perk_instance_id": 999, "position": 0})
        assert a.receive_json()["type"] == "ACTION_REJECTED"

        a.send_json(
            {"type": "APPLY_PERK", "perk_instance_id": sharpen_id, "position": 1}
        )
        assert a.receive_json()["you"]["hand"][1]["effect_value"] == 5

        a.send_json({"type": "CAST_WORD", "positions": [0, 1]})
        state = a.receive_json()
        b.receive_json()
        b.receive_json()
        assert state["your_turn"] is True and state["you"]["draft"] is not None

        a.send_json({"type": "REROLL_PERKS"})
        rerolled = a.receive_json()
        b.receive_json()
        assert rerolled["you"]["draft"]["rerolls_left"] == play.REROLLS_PER_MATCH - 1

        pick = rerolled["you"]["draft"]["options"][0]["perk_id"]
        a.send_json({"type": "SELECT_PERKS", "perk_ids": [pick]})
        after = a.receive_json()
        assert after["your_turn"] is False
        assert pick in [p["perk_id"] for p in after["you"]["perks"]]
