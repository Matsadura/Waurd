"""Replayable randomness."""

import random
import re

import pytest

pytest.importorskip("backend.game", reason="The game engine is not merged yet")

from backend.game.rng import new_seed, rng_for


def sample(rng: random.Random) -> list[float]:
    return [rng.random() for _ in range(5)]


def test_same_inputs_give_same_numbers() -> None:
    assert sample(rng_for("seed", 3, "deck", 1)) == sample(
        rng_for("seed", 3, "deck", 1)
    )


@pytest.mark.parametrize(
    ("seed", "turn", "purpose", "player"),
    [
        ("other-seed", 3, "deck", 1),
        ("seed", 4, "deck", 1),
        ("seed", 3, "draft", 1),
        ("seed", 3, "deck", 0),
        ("seed", 3, "deck", None),
    ],
    ids=["seed", "turn", "purpose", "player", "no-player"],
)
def test_every_argument_changes_the_numbers(
    seed: str, turn: int, purpose: str, player: int | None
) -> None:
    baseline = sample(rng_for("seed", 3, "deck", 1))

    assert sample(rng_for(seed, turn, purpose, player)) != baseline


def test_counters_in_the_purpose_give_new_numbers() -> None:
    first = sample(rng_for("seed", 3, "reshuffle:0", 0))
    second = sample(rng_for("seed", 3, "reshuffle:1", 0))

    assert first != second


def test_pinned_output() -> None:
    """Fails if seed derivation changes, which would break replays of saved
    matches. Only update these numbers on purpose."""
    rng = rng_for("waurd-pinned-seed", 3, "deck", player=1)

    assert rng.random() == 0.29067599397647825
    assert rng.randrange(1_000_000) == 987001
    assert rng_for("waurd-pinned-seed", 0, "first_player").randrange(2) == 0


def test_new_seed_is_random_hex() -> None:
    seeds = {new_seed() for _ in range(50)}

    assert len(seeds) == 50
    assert all(re.fullmatch(r"[0-9a-f]{32}", seed) for seed in seeds)
