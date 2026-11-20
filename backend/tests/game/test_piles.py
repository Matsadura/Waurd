"""Decks, starting a match, drawing and discarding."""

from collections import Counter

import pytest

pytest.importorskip("backend.game", reason="The game engine is not merged yet")

from backend.game.config import (
    DEFAULT_CONFIG,
    Effect,
    GameConfig,
    GlyphType,
    LetterSpec,
)
from backend.game.piles import build_deck, discard_hand, draw, new_match
from backend.game.state import Glyph, MatchState, Phase

USERS = ("user-a", "user-b")


def match(seed: str = "seed", **kwargs: object) -> MatchState:
    return new_match("match-1", USERS, 180, seed=seed, **kwargs)  # type: ignore[arg-type]


def ids(glyphs: list[Glyph]) -> list[str]:
    return [g.id for g in glyphs]


class TestBuildDeck:
    def test_follows_the_letter_table(self) -> None:
        deck = build_deck(0)

        assert len(deck) == 40
        counts = Counter(g.letters for g in deck)
        assert counts == {spec.letter: spec.copies for spec in DEFAULT_CONFIG.letters}
        b = next(g for g in deck if g.letters == "B")
        assert (b.type, b.effect, b.value) == (GlyphType.POWER, Effect.DAMAGE, 23)
        assert all(g.conditional_slot is None for g in deck)

    def test_ids_are_unique_and_name_the_player(self) -> None:
        deck0, deck1 = build_deck(0), build_deck(1)

        assert ids(deck0)[:2] == ["p0-g0", "p0-g1"]
        assert len(set(ids(deck0) + ids(deck1))) == 80
        assert all(i.startswith("p1-") for i in ids(deck1))

    def test_glyphs_are_separate_objects(self) -> None:
        deck = build_deck(0)

        deck[0].value = 999

        assert build_deck(0)[0].value != 999


class TestNewMatch:
    def test_second_player_starts_with_the_shield(self) -> None:
        for seed in ("a", "b", "c", "d"):
            state = match(seed)
            first = state.active_player

            assert state.players[first].defense == 0
            assert state.players[1 - first].defense == 35

    def test_shield_is_configurable(self) -> None:
        state = match(config=GameConfig(second_player_shield=0))
        assert [p.defense for p in state.players] == [0, 0]

    def test_starting_state(self) -> None:
        state = match()

        assert state.phase is Phase.WAITING
        assert state.turn == 0
        assert state.winner is None
        assert state.time_control_seconds == 180
        for player, user in zip(state.players, USERS, strict=True):
            assert player.user_id == user
            assert player.hp == 130
            assert player.clock_ms == 180_000
            assert player.rerolls_left == 3
            assert player.hand == [] and player.discard_pile == []
            assert len(player.draw_pile) == 40

    def test_same_seed_same_match(self) -> None:
        assert match("abc").to_dict() == match("abc").to_dict()

    def test_decks_are_shuffled(self) -> None:
        state = match()

        assert ids(state.players[0].draw_pile) != ids(build_deck(0))

    def test_players_get_different_shuffles(self) -> None:
        state = match()

        letters = [[g.letters for g in p.draw_pile] for p in state.players]
        assert letters[0] != letters[1]

    def test_seed_decides_the_first_player(self) -> None:
        firsts = {match(f"seed-{n}").active_player for n in range(40)}

        assert firsts == {0, 1}

    def test_generates_a_seed_when_none_is_given(self) -> None:
        a = new_match("m", USERS, 180)
        b = new_match("m", USERS, 180)

        assert a.seed != b.seed

    def test_rejects_unknown_time_control(self) -> None:
        with pytest.raises(ValueError, match="not an allowed time control"):
            new_match("m", USERS, 90, seed="s")

    def test_rejects_playing_yourself(self) -> None:
        with pytest.raises(ValueError, match="against themselves"):
            new_match("m", ("same", "same"), 180, seed="s")

    def test_uses_a_custom_config(self) -> None:
        config = GameConfig(
            hand_size=2,
            starting_hp=50,
            rerolls_per_match=0,
            letters=(LetterSpec("A", GlyphType.SKILL, Effect.HEAL, 5, 4),),
        )

        state = match(config=config)

        assert state.players[0].hp == 50
        assert state.players[0].rerolls_left == 0
        assert len(state.players[1].draw_pile) == 4


class TestDraw:
    def test_takes_from_the_top(self) -> None:
        state = match()
        top = ids(state.players[0].draw_pile[-3:])[::-1]

        drawn = draw(state, 0, 3)

        assert ids(drawn) == top
        assert ids(state.players[0].hand) == top
        assert len(state.players[0].draw_pile) == 37

    def test_only_touches_that_player(self) -> None:
        state = match()

        draw(state, 1, 7)

        assert state.players[0].hand == []
        assert len(state.players[1].hand) == 7

    def test_drawing_exactly_the_last_glyph(self) -> None:
        state = match()
        draw(state, 0, 39)
        discard_hand(state, 0)

        drawn = draw(state, 0, 1)

        player = state.players[0]
        assert len(drawn) == 1
        assert player.draw_pile == []
        assert len(player.discard_pile) == 39
        assert player.reshuffles == 0

    def test_reshuffles_mid_draw(self) -> None:
        state = match()
        draw(state, 0, 37)
        discard_hand(state, 0)

        drawn = draw(state, 0, 7)

        player = state.players[0]
        assert len(drawn) == 7
        assert len(player.draw_pile) == 33
        assert player.discard_pile == []
        assert player.reshuffles == 1

    def test_reshuffle_is_replayable(self) -> None:
        def play(seed: str) -> list[str]:
            state = match(seed)
            draw(state, 0, 37)
            discard_hand(state, 0)
            draw(state, 0, 7)
            return ids(state.players[0].hand)

        assert play("x") == play("x")

    def test_each_reshuffle_gets_its_own_order(self) -> None:
        state = match()
        player = state.players[0]
        orders = []
        for _ in range(3):
            draw(state, 0, len(player.draw_pile))
            discard_hand(state, 0)
            draw(state, 0, 1)
            orders.append(ids(player.hand) + ids(player.draw_pile))
            discard_hand(state, 0)
            draw(state, 0, len(player.draw_pile))
            discard_hand(state, 0)

        assert player.reshuffles == 3
        assert len({tuple(order) for order in orders}) == 3

    def test_draws_fewer_when_both_piles_are_empty(self) -> None:
        state = match()
        player = state.players[0]
        player.draw_pile = player.draw_pile[:2]

        drawn = draw(state, 0, 7)

        assert len(drawn) == 2
        assert len(player.hand) == 2

    def test_drawing_with_everything_in_hand(self) -> None:
        state = match()
        draw(state, 0, 40)

        assert draw(state, 0, 5) == []

    def test_drawing_zero(self) -> None:
        state = match()

        assert draw(state, 0, 0) == []

    def test_negative_count(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            draw(match(), 0, -1)

    @pytest.mark.parametrize("player", [-1, 2])
    def test_unknown_player(self, player: int) -> None:
        with pytest.raises(ValueError, match="Player index"):
            draw(match(), player, 1)


class TestDiscardHand:
    def test_moves_the_whole_hand(self) -> None:
        state = match()
        drawn = draw(state, 0, 7)

        discard_hand(state, 0)

        assert state.players[0].hand == []
        assert ids(state.players[0].discard_pile) == ids(drawn)

    def test_adds_to_an_existing_discard_pile(self) -> None:
        state = match()
        draw(state, 0, 3)
        discard_hand(state, 0)
        draw(state, 0, 4)

        discard_hand(state, 0)

        assert len(state.players[0].discard_pile) == 7


@pytest.mark.parametrize("seed", [f"long-{n}" for n in range(5)])
def test_many_turns_never_lose_or_duplicate_a_glyph(seed: str) -> None:
    state = match(seed)
    original = {p: sorted(ids(state.players[p].draw_pile)) for p in (0, 1)}

    for turn in range(1, 201):
        state.turn = turn
        player = turn % 2
        draw(state, player, DEFAULT_CONFIG.hand_size)
        assert len(state.players[player].hand) == DEFAULT_CONFIG.hand_size
        discard_hand(state, player)
        for p in (0, 1):
            current = ids(state.players[p].all_glyphs())
            assert sorted(current) == original[p]

    assert all(p.reshuffles > 0 for p in state.players)
