"""Drafting: after casting, the player is offered perks and keeps some.

- An offer holds up to `perks_per_turn` different perks, drawn from the
  catalog rows marked ready. For each slot a rarity is drawn by
  `rarity_weights`, then a perk of that rarity.
- A reroll replaces the whole offer; each player has `rerolls_per_match`.
- The player then picks exactly `perks_to_select` of the offered perks.

The offer is saved in PlayerState.draft_offer, so a reconnecting player sees
the same perks. Every draw uses rng_for, keyed by the turn and the number of
rerolls used, so a replay offers the same perks.

PLACEHOLDER rules, to confirm with the team:
- A rarity with no ready perks left is skipped and the others share its
  weight. An offer can be smaller than `perks_per_turn`, even empty.
- If fewer perks are offered than `perks_to_select`, the player takes them all.
- Perks the player already owns can be offered again.

Checking that it is the player's DRAFT phase is the turn's job (step 9).
"""

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from backend.game.config import DEFAULT_CONFIG, GameConfig
from backend.game.perks import PerkSpec, grant_perk, load_catalog
from backend.game.rng import rng_for
from backend.game.state import JSONDict, MatchState, PerkInstance


class DraftProblem(enum.StrEnum):
    NO_OFFER = "NO_OFFER"
    OFFER_ALREADY_OPEN = "OFFER_ALREADY_OPEN"
    NO_REROLLS_LEFT = "NO_REROLLS_LEFT"
    WRONG_PICK_COUNT = "WRONG_PICK_COUNT"
    PICK_OUT_OF_RANGE = "PICK_OUT_OF_RANGE"
    REPEATED_PICK = "REPEATED_PICK"


class DraftError(ValueError):
    """A draft move that can't be accepted; `problem` says why. The state is
    left unchanged."""

    def __init__(self, problem: DraftProblem, message: str) -> None:
        super().__init__(message)
        self.problem = problem


@dataclass(frozen=True, slots=True)
class DraftOffer:
    """An open draft. to_dict() is the DRAFT_OFFERED payload."""

    player: int
    options: tuple[PerkSpec, ...]
    picks_required: int
    rerolls_left: int

    def to_dict(self) -> JSONDict:
        return {
            "player": self.player,
            "options": [
                {
                    "perk_id": spec.id,
                    "name": spec.name,
                    "rarity": spec.rarity.value,
                    "description": spec.description,
                    "durability": spec.durability,
                    "targets": sorted(target.value for target in spec.targets),
                    "image": spec.image,
                    "quote": spec.quote,
                }
                for spec in self.options
            ],
            "picks_required": self.picks_required,
            "rerolls_left": self.rerolls_left,
        }


def _picks_required(offer: Sequence[str], config: GameConfig) -> int:
    return min(len(offer), config.perks_to_select)


def _offer(
    state: MatchState, player: int, catalog: Mapping[str, PerkSpec], config: GameConfig
) -> DraftOffer:
    side = state.player(player)
    return DraftOffer(
        player=player,
        options=tuple(catalog[perk_id] for perk_id in side.draft_offer),
        picks_required=_picks_required(side.draft_offer, config),
        rerolls_left=side.rerolls_left,
    )


def _draw(
    state: MatchState, player: int, catalog: Mapping[str, PerkSpec], config: GameConfig
) -> list[str]:
    rerolls_used = config.rerolls_per_match - state.player(player).rerolls_left
    rng = rng_for(state.seed, state.turn, f"draft:{rerolls_used}", player=player)

    by_rarity: dict[str, list[str]] = {}
    for spec in catalog.values():
        if spec.ready:
            by_rarity.setdefault(spec.rarity.value, []).append(spec.id)
    for ids in by_rarity.values():
        # Sorted, so the draw doesn't depend on row order in the CSV.
        ids.sort()

    offer: list[str] = []
    while len(offer) < config.perks_per_turn:
        choices = [
            (rarity.value, weight)
            for rarity, weight in config.rarity_weights
            if weight > 0 and by_rarity.get(rarity.value)
        ]
        if not choices:
            break
        [rarity] = rng.choices(
            [rarity for rarity, _ in choices],
            weights=[weight for _, weight in choices],
        )
        pool = by_rarity[rarity]
        offer.append(pool.pop(rng.randrange(len(pool))))
    return offer


def open_draft(
    state: MatchState,
    player: int,
    catalog: Mapping[str, PerkSpec] | None = None,
    config: GameConfig = DEFAULT_CONFIG,
) -> DraftOffer:
    """Draw a new offer for the player. Raises DraftError if one is open."""
    catalog = load_catalog() if catalog is None else catalog
    side = state.player(player)
    if side.draft_offer:
        raise DraftError(
            DraftProblem.OFFER_ALREADY_OPEN, "Pick from the open draft first."
        )
    side.draft_offer = _draw(state, player, catalog, config)
    return _offer(state, player, catalog, config)


def reroll_draft(
    state: MatchState,
    player: int,
    catalog: Mapping[str, PerkSpec] | None = None,
    config: GameConfig = DEFAULT_CONFIG,
) -> DraftOffer:
    """Spend a reroll to replace the open offer with a new one."""
    catalog = load_catalog() if catalog is None else catalog
    side = state.player(player)
    if not side.draft_offer:
        raise DraftError(DraftProblem.NO_OFFER, "There is no draft to reroll.")
    if side.rerolls_left <= 0:
        raise DraftError(DraftProblem.NO_REROLLS_LEFT, "No rerolls left this match.")
    side.rerolls_left -= 1
    side.draft_offer = _draw(state, player, catalog, config)
    return _offer(state, player, catalog, config)


def select_perks(
    state: MatchState,
    player: int,
    picks: Sequence[int],
    catalog: Mapping[str, PerkSpec] | None = None,
    config: GameConfig = DEFAULT_CONFIG,
) -> list[PerkInstance]:
    """Keep the offered perks at `picks` (0-based positions in the offer),
    give them to the player and close the draft."""
    catalog = load_catalog() if catalog is None else catalog
    side = state.player(player)
    offer = side.draft_offer
    required = _picks_required(offer, config)
    if not offer and required == 0 and not picks:
        # Nothing could be offered; the draft just closes.
        return []
    if not offer:
        raise DraftError(DraftProblem.NO_OFFER, "There is no draft to pick from.")
    if len(picks) != required:
        raise DraftError(
            DraftProblem.WRONG_PICK_COUNT, f"Pick exactly {required} perk(s)."
        )
    seen: set[int] = set()
    for pick in picks:
        if (
            not isinstance(pick, int)
            or isinstance(pick, bool)
            or not 0 <= pick < len(offer)
        ):
            raise DraftError(
                DraftProblem.PICK_OUT_OF_RANGE, f"Pick {pick!r} is not in the offer."
            )
        if pick in seen:
            raise DraftError(DraftProblem.REPEATED_PICK, f"Pick {pick} is used twice.")
        seen.add(pick)

    chosen = [offer[pick] for pick in picks]
    side.draft_offer = []
    return [grant_perk(state, player, perk_id, catalog) for perk_id in chosen]
