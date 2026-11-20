"""GameConfig: placeholder defaults and validation."""

import dataclasses
from typing import Any

import pytest

pytest.importorskip("backend.game", reason="The game engine is not merged yet")

from backend.game.config import (
    DEFAULT_CONFIG,
    DEFAULT_LETTERS,
    Effect,
    GameConfig,
    GlyphType,
    LetterSpec,
    Rarity,
)


class TestDefaults:
    def test_placeholder_numbers(self) -> None:
        config = GameConfig()

        assert config.hand_size == 7
        assert config.deck_size == 40
        assert config.perks_per_turn == 3
        assert config.perks_to_select == 1
        assert config.rerolls_per_match == 3
        assert config.starting_hp == 100
        assert config.time_controls == (180, 300, 600)
        assert config.second_player_shield == 30
        assert config.vulnerable_percent == config.weak_percent == 25
        assert config.defense_carries_over is False

    def test_rarity_weights_add_up_to_100(self) -> None:
        assert dict(DEFAULT_CONFIG.rarity_weights) == {
            Rarity.COMMON: 60,
            Rarity.UNCOMMON: 25,
            Rarity.RARE: 12,
            Rarity.LEGENDARY: 3,
        }

    def test_letter_table_is_the_balanced_one(self) -> None:
        table = {spec.letter: spec for spec in DEFAULT_LETTERS}

        assert len(table) == 23
        assert set("JQX").isdisjoint(table)
        assert table["B"] == LetterSpec("B", GlyphType.POWER, Effect.DAMAGE, 23, 1)
        assert table["R"] == LetterSpec("R", GlyphType.SKILL, Effect.DEFENSE, 14, 2)
        assert table["A"] == LetterSpec("A", GlyphType.SKILL, Effect.HEAL, 9, 3)
        assert table["V"] == LetterSpec("V", GlyphType.SKILL, Effect.VULNERABLE, 2, 1)
        assert table["E"] == LetterSpec("E", GlyphType.SKILL, Effect.WEAK, 2, 4)
        assert table["Z"] == LetterSpec("Z", GlyphType.POWER, Effect.DAMAGE, 29, 1)

    def test_letter_lookup(self) -> None:
        assert DEFAULT_CONFIG.letter("K").value == 21
        with pytest.raises(KeyError):
            DEFAULT_CONFIG.letter("Q")

    def test_is_immutable(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            DEFAULT_CONFIG.hand_size = 9  # type: ignore[misc]


def letters_with(**changes: Any) -> tuple[LetterSpec, ...]:
    return (dataclasses.replace(DEFAULT_LETTERS[0], **changes), *DEFAULT_LETTERS[1:])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"hand_size": 0}, "hand_size must be at least 1"),
        ({"hand_size": 41}, "bigger than the 40-glyph deck"),
        ({"perks_per_turn": 0}, "perks_per_turn must be at least 1"),
        ({"perks_to_select": 4}, "perks_to_select must be between"),
        ({"perks_to_select": 0}, "perks_to_select must be between"),
        ({"rerolls_per_match": -1}, "rerolls_per_match can't be negative"),
        ({"starting_hp": 0}, "starting_hp must be between"),
        ({"starting_hp": 150}, "starting_hp must be between"),
        ({"time_controls": ()}, "time_controls must be positive"),
        ({"time_controls": (60, 0)}, "time_controls must be positive"),
        ({"time_controls": (60, 60)}, "time_controls has a duplicate"),
        ({"second_player_shield": -1}, "second_player_shield can't be negative"),
        ({"vulnerable_percent": 101}, "vulnerable_percent must be between"),
        ({"weak_percent": -5}, "weak_percent must be between"),
        (
            {"rarity_weights": ((Rarity.COMMON, 60), (Rarity.RARE, 28))},
            "add up to 88, not 100",
        ),
        (
            {
                "rarity_weights": (
                    (Rarity.COMMON, 60),
                    (Rarity.UNCOMMON, 28),
                    (Rarity.RARE, 15),
                    (Rarity.LEGENDARY, 3),
                )
            },
            "add up to 106, not 100",
        ),
        (
            {"rarity_weights": ((Rarity.COMMON, 50), (Rarity.COMMON, 50))},
            "duplicate rarity",
        ),
        (
            {"rarity_weights": ((Rarity.COMMON, 110), (Rarity.RARE, -10))},
            "can't be negative",
        ),
        ({"letters": ()}, "letter table is empty"),
        (
            {"letters": (*DEFAULT_LETTERS, DEFAULT_LETTERS[0])},
            "Letter A appears twice",
        ),
        ({"letters": letters_with(letter="a")}, "not a single letter"),
        ({"letters": letters_with(letter="AB")}, "not a single letter"),
        ({"letters": letters_with(copies=0)}, "needs at least 1 copy"),
        ({"letters": letters_with(value=-1)}, "has value -1"),
        (
            {"letters": letters_with(effect=Effect.WEAK, value=0)},
            "has value 0",
        ),
    ],
)
def test_invalid_config_is_rejected(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        GameConfig(**overrides)


def test_hand_can_equal_the_deck() -> None:
    assert GameConfig(hand_size=40).hand_size == 40


def test_smaller_custom_table() -> None:
    config = GameConfig(
        hand_size=3,
        letters=(LetterSpec("A", GlyphType.SKILL, Effect.HEAL, 5, 3),),
    )

    assert config.deck_size == 3
