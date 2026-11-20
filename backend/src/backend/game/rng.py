"""Randomness that can be replayed.

Every random decision gets its own generator, derived from the match seed, the
turn, the player and a purpose such as "deck" or "draft". Given the same seed,
a match makes exactly the same random choices again, which keeps replays and
bug reports reproducible. This is the only engine module allowed to import
random, and it only uses random.Random.
"""

import random
import secrets

# The generator type, for annotations elsewhere in the engine.
Rng = random.Random


def rng_for(seed: str, turn: int, purpose: str, player: int | None = None) -> Rng:
    """Return the generator for one random decision.

    String seeds are hashed with SHA-512 by random.Random, so the numbers are
    the same in every process (unlike hash()). Changing this derivation would
    break replays of existing matches.
    """
    return random.Random(f"{seed}:{turn}:{player}:{purpose}")


def new_seed() -> str:
    """Return a fresh, unpredictable match seed."""
    return secrets.token_hex(16)
