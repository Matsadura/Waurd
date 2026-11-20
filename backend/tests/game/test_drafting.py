"""Drafting: rarity-weighted offers, rerolls per match and picking perks."""

import json
from collections import Counter
from dataclasses import replace

import pytest

pytest.importorskip("backend.game.drafting", reason="Drafting is not merged yet")

from backend.game.drafting import (
    DraftError,
    DraftProblem,
    open_draft,
    reroll_draft,
    select_perks,
)

from backend.game.config import GameConfig, Rarity
from backend.game.perks import load_catalog
from backend.game.piles import new_match
from backend.game.state import MatchState

ALL_READY = {pid: replace(spec, ready=True) for pid, spec in load_catalog().items()}
RARE_ONLY = GameConfig(
    rarity_weights=(
        (Rarity.COMMON, 0),
        (Rarity.UNCOMMON, 0),
        (Rarity.RARE, 100),
        (Rarity.LEGENDARY, 0),
    )
)


def match(seed: str = "seed", turn: int = 1) -> MatchState:
    state = new_match("match-1", ("user-a", "user-b"), 180, seed=seed)
    state.turn = turn
    return state


def ready_only(*perk_ids: str):  # type: ignore[no-untyped-def]
    return {
        pid: replace(spec, ready=pid in perk_ids)
        for pid, spec in load_catalog().items()
    }


class TestOffer:
    def test_offers_distinct_ready_perks(self) -> None:
        state = match()

        offer = open_draft(state, 0, ALL_READY)

        ids = [spec.id for spec in offer.options]
        assert len(ids) == 3 == len(set(ids))
        assert state.players[0].draft_offer == ids
        assert offer.picks_required == 1
        assert offer.rerolls_left == 3

    def test_not_ready_perks_are_never_offered(self) -> None:
        catalog = ready_only("amplify", "ing", "erase", "er")
        for seed in range(30):
            offer = open_draft(match(str(seed)), 0, catalog)
            assert {s.id for s in offer.options} <= {"amplify", "ing", "erase", "er"}

    def test_bundled_catalog_has_nothing_ready_yet(self) -> None:
        state = match()

        offer = open_draft(state, 0)

        assert offer.options == ()
        assert offer.picks_required == 0
        assert select_perks(state, 0, []) == []
        assert state.players[0].perks == []

    def test_small_pool_offers_what_there_is(self) -> None:
        state = match()

        offer = open_draft(state, 0, ready_only("amplify", "ing"))

        assert {s.id for s in offer.options} == {"amplify", "ing"}
        assert offer.picks_required == 1

    def test_same_seed_and_turn_give_the_same_offer(self) -> None:
        first = open_draft(match("x", turn=3), 0, ALL_READY)
        second = open_draft(match("x", turn=3), 0, ALL_READY)

        assert first == second

    def test_each_turn_draws_a_new_offer(self) -> None:
        offers = {
            tuple(s.id for s in open_draft(match("x", turn=t), 0, ALL_READY).options)
            for t in range(1, 6)
        }
        assert len(offers) > 1

    def test_each_player_draws_their_own_offer(self) -> None:
        differs = False
        for seed in range(5):
            state = match(str(seed))
            mine = open_draft(state, 0, ALL_READY).options
            theirs = open_draft(state, 1, ALL_READY).options
            differs |= mine != theirs
        assert differs

    def test_zero_weight_rarities_are_never_drawn(self) -> None:
        # Two rare perks and plenty of commons are ready; only rares have weight.
        catalog = ready_only("amplify", "last_times_2", "er", "re", "last_plus_5")
        for seed in range(20):
            offer = open_draft(match(str(seed)), 0, catalog, RARE_ONLY)

            # The offer stops when the rares run out instead of using commons.
            assert {s.id for s in offer.options} == {"amplify", "last_times_2"}

    def test_rarities_follow_the_weights(self) -> None:
        # No legendary perks exist, so their 3% is shared: 60/97, 25/97, 12/97.
        counts: Counter[Rarity] = Counter()
        runs = 3000
        for seed in range(runs):
            offer = open_draft(match(f"w{seed}"), 0, ALL_READY)
            counts[offer.options[0].rarity] += 1

        assert counts[Rarity.LEGENDARY] == 0
        assert counts[Rarity.COMMON] / runs == pytest.approx(60 / 97, abs=0.04)
        assert counts[Rarity.UNCOMMON] / runs == pytest.approx(25 / 97, abs=0.04)
        assert counts[Rarity.RARE] / runs == pytest.approx(12 / 97, abs=0.03)

    def test_cannot_open_a_second_offer(self) -> None:
        state = match()
        open_draft(state, 0, ALL_READY)
        before = state.to_dict()

        with pytest.raises(DraftError) as caught:
            open_draft(state, 0, ALL_READY)

        assert caught.value.problem == DraftProblem.OFFER_ALREADY_OPEN
        assert state.to_dict() == before

    def test_payload_is_json_safe(self) -> None:
        offer = open_draft(match(), 0, ready_only("matching_ends_x2"))

        payload = json.loads(json.dumps(offer.to_dict()))

        assert payload == {
            "player": 0,
            "options": [
                {
                    "perk_id": "matching_ends_x2",
                    "name": "Matching Ends x2",
                    "rarity": "COMMON",
                    "description": ALL_READY["matching_ends_x2"].description,
                    "durability": None,
                    "targets": ["POWER", "SKILL"],
                    "image": None,
                    "quote": None,
                }
            ],
            "picks_required": 1,
            "rerolls_left": 3,
        }


class TestReroll:
    def test_spends_a_reroll_and_draws_again(self) -> None:
        changed = False
        for seed in range(10):
            state = match(str(seed))
            first = open_draft(state, 0, ALL_READY)

            second = reroll_draft(state, 0, ALL_READY)

            assert second.rerolls_left == state.players[0].rerolls_left == 2
            assert state.players[0].draft_offer == [s.id for s in second.options]
            changed |= first.options != second.options
        assert changed

    def test_reroll_is_replayable(self) -> None:
        def run() -> list[str]:
            state = match("r")
            open_draft(state, 0, ALL_READY)
            reroll_draft(state, 0, ALL_READY)
            return [s.id for s in reroll_draft(state, 0, ALL_READY).options]

        assert run() == run()

    def test_rerolls_run_out_for_the_match(self) -> None:
        state = match()
        open_draft(state, 0, ALL_READY)
        for _ in range(3):
            reroll_draft(state, 0, ALL_READY)
        before = state.to_dict()

        with pytest.raises(DraftError) as caught:
            reroll_draft(state, 0, ALL_READY)

        assert caught.value.problem == DraftProblem.NO_REROLLS_LEFT
        assert state.to_dict() == before

    def test_rerolls_carry_over_to_later_turns(self) -> None:
        state = match()
        open_draft(state, 0, ALL_READY)
        reroll_draft(state, 0, ALL_READY)
        select_perks(state, 0, [0], ALL_READY)

        state.turn = 3
        offer = open_draft(state, 0, ALL_READY)

        assert offer.rerolls_left == 2

    def test_needs_an_open_offer(self) -> None:
        state = match()

        with pytest.raises(DraftError) as caught:
            reroll_draft(state, 0, ALL_READY)

        assert caught.value.problem == DraftProblem.NO_OFFER
        assert state.players[0].rerolls_left == 3


class TestSelect:
    def test_grants_the_pick_and_closes_the_draft(self) -> None:
        state = match()
        offer = open_draft(state, 0, ALL_READY)

        [instance] = select_perks(state, 0, [1], ALL_READY)

        chosen = offer.options[1]
        assert instance.perk_id == chosen.id
        assert instance.durability == chosen.durability
        assert state.players[0].perks == [instance]
        assert state.players[0].draft_offer == []
        assert state.players[1].perks == []

    def test_several_picks_when_configured(self) -> None:
        config = GameConfig(perks_to_select=2)
        state = match()
        offer = open_draft(state, 0, ALL_READY, config)
        assert offer.picks_required == 2

        instances = select_perks(state, 0, [2, 0], ALL_READY, config)

        assert [i.perk_id for i in instances] == [
            offer.options[2].id,
            offer.options[0].id,
        ]
        assert len({i.instance_id for i in instances}) == 2

    @pytest.mark.parametrize(
        ("picks", "problem"),
        [
            ([], DraftProblem.WRONG_PICK_COUNT),
            ([0, 1], DraftProblem.WRONG_PICK_COUNT),
            ([3], DraftProblem.PICK_OUT_OF_RANGE),
            ([-1], DraftProblem.PICK_OUT_OF_RANGE),
            ([True], DraftProblem.PICK_OUT_OF_RANGE),
        ],
    )
    def test_bad_picks_change_nothing(
        self, picks: list[int], problem: DraftProblem
    ) -> None:
        state = match()
        open_draft(state, 0, ALL_READY)
        before = state.to_dict()

        with pytest.raises(DraftError) as caught:
            select_perks(state, 0, picks, ALL_READY)

        assert caught.value.problem == problem
        assert state.to_dict() == before

    def test_repeated_pick(self) -> None:
        config = GameConfig(perks_to_select=2)
        state = match()
        open_draft(state, 0, ALL_READY, config)

        with pytest.raises(DraftError) as caught:
            select_perks(state, 0, [1, 1], ALL_READY, config)

        assert caught.value.problem == DraftProblem.REPEATED_PICK
        assert state.players[0].perks == []

    def test_needs_an_open_offer(self) -> None:
        state = match()

        with pytest.raises(DraftError) as caught:
            select_perks(state, 0, [0], ALL_READY)

        assert caught.value.problem == DraftProblem.NO_OFFER

    def test_small_offer_takes_everything_when_picks_exceed_it(self) -> None:
        config = GameConfig(perks_to_select=2)
        state = match()
        offer = open_draft(state, 0, ready_only("amplify"), config)
        assert offer.picks_required == 1

        [instance] = select_perks(state, 0, [0], ready_only("amplify"), config)

        assert instance.perk_id == "amplify"

    def test_open_offer_survives_a_save(self) -> None:
        state = match()
        offer = open_draft(state, 0, ALL_READY)

        restored = MatchState.from_dict(json.loads(json.dumps(state.to_dict())))

        assert restored.players[0].draft_offer == [s.id for s in offer.options]
        [instance] = select_perks(restored, 0, [0], ALL_READY)
        assert instance.perk_id == offer.options[0].id
