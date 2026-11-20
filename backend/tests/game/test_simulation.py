"""Simulated bot-vs-bot matches: 1,000 seeded matches keep every rule."""

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip(
    "backend.game.simulation", reason="The simulation is not merged yet"
)

from backend.game.simulation import (
    BotStyle,
    InvariantError,
    MatchSummary,
    SimulationReport,
    WordFinder,
    simulate,
)

from backend.core.dictionary import load_word_list
from backend.game import simulation, turns
from backend.game.config import Effect, GameConfig, GlyphType
from backend.game.perks import load_catalog
from backend.game.state import EndReason, Glyph, Status

ALL_READY = {pid: replace(spec, ready=True) for pid, spec in load_catalog().items()}


@pytest.fixture(scope="module")
def finder() -> WordFinder:
    return WordFinder(load_word_list())


def glyph(n: int, letters: str) -> Glyph:
    return Glyph(f"g{n}", letters, GlyphType.POWER, Effect.DAMAGE, 8)


class TestThousandMatches:
    def test_every_rule_holds_with_every_perk_in_play(self, finder: WordFinder) -> None:
        style = BotStyle(resign_chance=0.01, disconnect_chance=0.01)

        report = simulate(finder, matches=1000, catalog=ALL_READY, style=style)

        assert len(report.matches) == 1000
        assert all(m.end_reason is not None for m in report.matches)
        reasons = {m.end_reason for m in report.matches}
        assert reasons == set(EndReason)
        summary = report.summary()
        assert summary["perks_applied"] > 0
        assert summary["glyphs_erased"] > 0
        assert 0 < summary["first_player_win_rate"] < 1

    def test_rules_hold_with_the_catalog_as_it_is(self, finder: WordFinder) -> None:
        report = simulate(finder, matches=300)

        assert report.summary()["perks_applied"] == 0
        assert {m.end_reason for m in report.matches} <= {
            EndReason.HEALTH_DEPLETED,
            EndReason.TIMEOUT,
        }

    def test_seeds_replay_exactly(self, finder: WordFinder) -> None:
        first = simulate(finder, matches=20, catalog=ALL_READY)
        second = simulate(finder, matches=20, catalog=ALL_READY)

        assert first.matches == second.matches

    def test_other_seeds_play_other_matches(self, finder: WordFinder) -> None:
        a = simulate(finder, matches=10, seed_prefix="a")
        b = simulate(finder, matches=10, seed_prefix="b")

        assert [m.words for m in a.matches] != [m.words for m in b.matches]


class TestBalance:
    """Guards the balance from scripts/simulate.py: change the values or the
    CSV and these say whether matches got too long, too short or one-sided."""

    @pytest.fixture(scope="class")
    def csv_report(self, finder: WordFinder) -> SimulationReport:
        return simulate(finder, matches=600, seed_prefix="balance")

    @pytest.fixture(scope="class")
    def perks_report(self, finder: WordFinder) -> SimulationReport:
        return simulate(finder, matches=600, catalog=ALL_READY, seed_prefix="balance")

    @pytest.mark.parametrize("report", ["csv_report", "perks_report"])
    def test_matches_are_neither_long_nor_short(self, report: str, request) -> None:  # type: ignore[no-untyped-def]
        summary = request.getfixturevalue(report).summary()

        assert 10 <= summary["turns_median"] <= 20
        assert summary["turns_max"] <= 60

    @pytest.mark.parametrize("report", ["csv_report", "perks_report"])
    def test_turn_order_is_fair(self, report: str, request) -> None:  # type: ignore[no-untyped-def]
        assert 0.42 <= request.getfixturevalue(report).first_player_win_rate <= 0.58

    @pytest.mark.parametrize("report", ["csv_report", "perks_report"])
    def test_the_clock_rarely_decides(self, report: str, request) -> None:  # type: ignore[no-untyped-def]
        assert request.getfixturevalue(report).summary()["timeout_share"] < 0.05

    def test_bot_passes_instead_of_waiting(self, csv_report: SimulationReport) -> None:
        assert csv_report.summary()["turns_passed_or_stuck"] > 0


class TestBotOptions:
    def test_config_is_used_for_the_matches(self, finder: WordFinder) -> None:
        config = GameConfig(time_controls=(1234,))

        report = simulate(finder, matches=3, config=config)

        assert all(max(m.seconds_used) <= 1234 for m in report.matches)

    def test_waiting_out_the_clock_ends_matches_on_time(
        self, finder: WordFinder
    ) -> None:
        style = BotStyle(pass_when_stuck=False)

        report = simulate(finder, matches=150, style=style)

        stuck = [m for m in report.matches if m.turns_without_a_word]
        assert stuck
        assert all(m.end_reason == EndReason.TIMEOUT for m in stuck)

    def test_random_word_choice(self, finder: WordFinder) -> None:
        random = simulate(finder, matches=100, style=BotStyle(choose_from_best=None))
        good = simulate(finder, matches=100)

        assert random.summary()["word_length_mean"] < good.summary()["word_length_mean"]


class TestTheChecksCatchBugs:
    def test_a_lost_glyph_is_reported_with_its_seed(
        self, finder: WordFinder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = turns.discard_hand

        def leaky(state, player):  # type: ignore[no-untyped-def]
            hand = state.player(player).hand
            if hand:
                hand.pop()
            real(state, player)

        monkeypatch.setattr(turns, "discard_hand", leaky)

        with pytest.raises(InvariantError, match=r"seed 'sim-0', action \d+: .*glyphs"):
            simulate(finder, matches=1)

    def test_a_rejected_move_is_reported(
        self, finder: WordFinder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(turns, "validate_cast", _always_unknown)

        with pytest.raises(InvariantError, match="legal move rejected"):
            simulate(finder, matches=1)

    def test_a_match_that_never_ends_is_reported(self, finder: WordFinder) -> None:
        with pytest.raises(InvariantError, match="no end after 5 actions"):
            simulate(finder, matches=1, max_actions=5)

    def test_hp_out_of_bounds_is_reported(
        self, finder: WordFinder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = turns.resolve_word

        def overheal(state, caster, positions, **kwargs):  # type: ignore[no-untyped-def]
            result = real(state, caster, positions, **kwargs)
            state.player(caster).hp += 1000
            return result

        monkeypatch.setattr(turns, "resolve_word", overheal)

        with pytest.raises(InvariantError, match="HP is"):
            simulate(finder, matches=1)


def _wrap(name: str, after):  # type: ignore[no-untyped-def]
    """Patch turns.<name> to run `after(state, result, *args)` once it returns."""
    real = getattr(turns, name)

    def patched(state, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = real(state, *args, **kwargs)
        after(state, result, *args)
        return result

    return name, patched


def _duplicate_glyph(state, result, player):  # type: ignore[no-untyped-def]
    pile = state.player(player).discard_pile
    if len(pile) >= 2:
        pile[0] = replace(pile[1])


def _zero_durability_perk(state, result, player, *args):  # type: ignore[no-untyped-def]
    for perk in state.player(player).perks:
        perk.durability = 0


def _expired_status(state, result, caster, *args):  # type: ignore[no-untyped-def]
    state.player(1 - caster).statuses.append(Status(Effect.WEAK, 0))


def _negative_defense(state, result, caster, *args):  # type: ignore[no-untyped-def]
    state.player(1 - caster).defense = -1


def _keep_hand(state, result, player):  # type: ignore[no-untyped-def]
    state.player(player).hand.append(state.player(player).discard_pile.pop())


def _extra_time(state, result, now_ms):  # type: ignore[no-untyped-def]
    state.player(state.active_player).clock_ms += 10_000_000


def _turn_back(state, result, config):  # type: ignore[no-untyped-def]
    state.turn -= 2


def _no_winner(state, result, winner, reason):  # type: ignore[no-untyped-def]
    state.winner = None


def _loser_keeps_hp(state, result, winner, reason):  # type: ignore[no-untyped-def]
    state.player(1 - winner).hp = 5


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        (_wrap("discard_hand", _duplicate_glyph), "in two places"),
        (_wrap("apply_perk", _zero_durability_perk), "at 0"),
        (_wrap("resolve_word", _expired_status), "expired status"),
        (_wrap("resolve_word", _negative_defense), "defense/clock below 0"),
        (_wrap("discard_hand", _keep_hand), "waiting player .* holds a hand"),
        (_wrap("charge", _extra_time), "clock above the time control"),
        (_wrap("_end_turn", _turn_back), "turn number went back"),
        (_wrap("_end_match", _no_winner), "don't match the phase"),
        (_wrap("_end_match", _loser_keeps_hp), "loser has HP"),
    ],
    ids=lambda value: value[0] if isinstance(value, tuple) else None,
)
def test_each_check_fires(
    finder: WordFinder,
    monkeypatch: pytest.MonkeyPatch,
    patch,
    message: str,  # type: ignore[no-untyped-def]
) -> None:
    name, patched = patch
    monkeypatch.setattr(turns, name, patched)

    with pytest.raises(InvariantError, match=message):
        simulate(finder, matches=20, catalog=ALL_READY)


def _always_unknown(*args, **kwargs):  # type: ignore[no-untyped-def]
    from backend.game.spelling import SpellingError, SpellingProblem

    raise SpellingError(SpellingProblem.UNKNOWN_WORD, "nope")


class TestWordFinder:
    def test_finds_words_and_their_glyph_order(self) -> None:
        finder = WordFinder(["cab", "bat", "at"])
        hand = [glyph(0, "T"), glyph(1, "B"), glyph(2, "A"), glyph(3, "C")]

        plays = finder.plays(hand)

        words = sorted("".join(hand[i].letters for i in play) for play in plays)
        assert words == ["AT", "BAT", "CAB"]

    def test_multi_letter_glyphs(self) -> None:
        finder = WordFinder(["sing", "sings", "gins"])
        hand = [glyph(0, "S"), glyph(1, "ING"), glyph(2, "S")]

        words = {"".join(hand[i].letters for i in p) for p in finder.plays(hand)}

        assert words == {"SING", "SINGS"}

    def test_no_words(self) -> None:
        assert WordFinder(["cab"]).plays([glyph(0, "Z"), glyph(1, "Q")]) == []

    def test_works_as_a_dictionary(self) -> None:
        finder = WordFinder(["cab"])
        assert "CAB" in finder and "cab" in finder and "BAT" not in finder


class TestReport:
    def summary(
        self, first: int, winner: int | None, reason: EndReason
    ) -> MatchSummary:
        return MatchSummary(
            "s", first, winner, reason, turns=10, actions=20, words=["AT", "CAB"]
        )

    def test_first_player_win_rate(self) -> None:
        report = SimulationReport(
            [
                self.summary(0, 0, EndReason.TIMEOUT),
                self.summary(1, 0, EndReason.HEALTH_DEPLETED),
                self.summary(1, 1, EndReason.RESIGNATION),
                self.summary(0, 0, EndReason.TIMEOUT),
            ]
        )

        assert report.first_player_win_rate == 0.75
        summary = report.summary()
        assert summary["end_reasons"] == {
            "TIMEOUT": 2,
            "HEALTH_DEPLETED": 1,
            "RESIGNATION": 1,
        }
        assert summary["word_length_mean"] == 2.5
        assert summary["turns_mean"] == 10


def test_script_prints_the_stats() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/simulate.py", "--matches", "6", "--all-perks"],
        # The backend folder of the code under test.
        cwd=Path(simulation.__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "6 matches in" in result.stdout
    assert "13 perks in drafts" in result.stdout
    assert "first_player_win_rate:" in result.stdout
