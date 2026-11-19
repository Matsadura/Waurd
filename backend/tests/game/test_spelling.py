"""Spelling words from hand positions and validating them."""

import pytest

pytest.importorskip("backend.game.spelling", reason="Spelling is not merged yet")

from backend.game.config import Effect, GlyphType
from backend.game.spelling import (
    Dictionary,
    SpellingError,
    SpellingProblem,
    check_word,
    selected_glyphs,
    spell,
    validate_cast,
)
from backend.game.state import Glyph

WORDS: frozenset[str] = frozenset({"CAB", "BAT", "SING", "SINGER", "AT"})


def glyph(n: int, letters: str) -> Glyph:
    return Glyph(f"p0-g{n}", letters, GlyphType.POWER, Effect.DAMAGE, 8)


# Hand positions: 0=C 1=A 2=B 3=T 4=S 5=ING 6=ER
HAND = [
    glyph(0, "C"),
    glyph(1, "A"),
    glyph(2, "B"),
    glyph(3, "T"),
    glyph(4, "S"),
    glyph(5, "ING"),
    glyph(6, "ER"),
]


def problem_of(error: pytest.ExceptionInfo[SpellingError]) -> SpellingProblem:
    return error.value.problem


class TestSpell:
    def test_follows_the_position_order(self) -> None:
        assert spell(HAND, [0, 1, 2]) == "CAB"
        assert spell(HAND, [2, 1, 3]) == "BAT"

    def test_multi_letter_glyphs_add_all_their_letters(self) -> None:
        assert spell(HAND, [4, 5]) == "SING"
        assert spell(HAND, [4, 5, 6]) == "SINGER"

    def test_selected_glyphs_keep_identity_and_order(self) -> None:
        assert [g.id for g in selected_glyphs(HAND, [3, 1])] == ["p0-g3", "p0-g1"]

    def test_does_not_change_the_hand(self) -> None:
        before = [g.id for g in HAND]

        spell(HAND, [2, 1, 3])

        assert [g.id for g in HAND] == before

    def test_accepts_tuples(self) -> None:
        assert spell(tuple(HAND), (1, 3)) == "AT"

    def test_no_positions(self) -> None:
        with pytest.raises(SpellingError) as error:
            spell(HAND, [])

        assert problem_of(error) is SpellingProblem.NO_GLYPHS

    @pytest.mark.parametrize("position", [7, 100, -1, -7])
    def test_position_outside_the_hand(self, position: int) -> None:
        with pytest.raises(SpellingError) as error:
            spell(HAND, [0, position])

        assert problem_of(error) is SpellingProblem.POSITION_OUT_OF_RANGE

    @pytest.mark.parametrize("position", [True, 1.0, "1", None])
    def test_position_must_be_an_integer(self, position: object) -> None:
        with pytest.raises(SpellingError) as error:
            spell(HAND, [0, position])  # type: ignore[list-item]

        assert problem_of(error) is SpellingProblem.POSITION_OUT_OF_RANGE

    def test_repeated_position(self) -> None:
        with pytest.raises(SpellingError) as error:
            spell(HAND, [2, 1, 2])

        assert problem_of(error) is SpellingProblem.REPEATED_POSITION
        assert "Position 2 is used twice" in str(error.value)

    def test_empty_hand(self) -> None:
        with pytest.raises(SpellingError) as error:
            spell([], [0])

        assert problem_of(error) is SpellingProblem.POSITION_OUT_OF_RANGE

    def test_errors_are_value_errors(self) -> None:
        with pytest.raises(ValueError):
            spell(HAND, [])


class TestCheckWord:
    def test_known_word(self) -> None:
        check_word("CAB", WORDS)

    def test_lowercase_input_is_normalised(self) -> None:
        check_word("cab", WORDS)

    def test_unknown_word(self) -> None:
        with pytest.raises(SpellingError) as error:
            check_word("CBA", WORDS)

        assert problem_of(error) is SpellingProblem.UNKNOWN_WORD
        assert "CBA is not a valid word" in str(error.value)

    def test_achievement_words_count(self) -> None:
        check_word("WAURD", WORDS, achievement_words={"WAURD"})

    def test_achievement_words_ignore_case(self) -> None:
        check_word("WAURD", WORDS, achievement_words=["waurd"])

    def test_achievement_words_do_not_unlock_others(self) -> None:
        with pytest.raises(SpellingError):
            check_word("GLYPHS", WORDS, achievement_words={"WAURD"})

    def test_any_dictionary_object_works(self) -> None:
        class OnlyCab:
            def __contains__(self, word: object) -> bool:
                return word == "CAB"

        dictionary: Dictionary = OnlyCab()

        check_word("cab", dictionary)
        with pytest.raises(SpellingError):
            check_word("BAT", dictionary)


class TestValidateCast:
    def test_returns_the_word(self) -> None:
        assert validate_cast(HAND, [4, 5, 6], WORDS) == "SINGER"

    def test_rejects_an_unknown_word(self) -> None:
        with pytest.raises(SpellingError) as error:
            validate_cast(HAND, [1, 0, 2], WORDS)

        assert problem_of(error) is SpellingProblem.UNKNOWN_WORD

    def test_checks_positions_before_the_word(self) -> None:
        with pytest.raises(SpellingError) as error:
            validate_cast(HAND, [0, 0], WORDS)

        assert problem_of(error) is SpellingProblem.REPEATED_POSITION

    def test_achievement_word_from_the_hand(self) -> None:
        hand = [glyph(0, "Z"), glyph(1, "A"), glyph(2, "P")]

        assert validate_cast(hand, [0, 1, 2], WORDS, achievement_words={"ZAP"}) == "ZAP"
