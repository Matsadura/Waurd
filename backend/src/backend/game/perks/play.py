"""The rules every perk shares: drafting, holding, applying and durability.

A turn with perks: apply any perks to glyphs in your hand, cast a word, then
pick one of the offered perks (or skip). Picking ends the turn, and the clock
keeps running while you choose. Passing skips the draft too.
"""

from backend.game.models import Glyph, Match, PerkInstance
from backend.game.perks.catalog import CATALOG, PerkSpec
from backend.game.perks.effects import BONUS, DIRECT, PerkContext, is_status

DRAFT_SIZE = 3  # perks offered after each cast
REROLLS_PER_MATCH = 3
RARITY_WEIGHTS = {"common": 60, "uncommon": 25, "rare": 12, "legendary": 3}
TARGET_EFFECTS = {
    "damage": {"damage"},
    "heal_defense": {"heal", "defense"},
    "any": {"damage", "heal", "defense", "vulnerable", "weak"},
}


def spec(perk_id: str) -> PerkSpec:
    return CATALOG[perk_id]


def grant(match: Match, player_index: int, perk_id: str) -> PerkInstance:
    """Give a player a fresh copy of a perk, at its full durability."""
    instance = PerkInstance(match.next_perk_id, perk_id, spec(perk_id).durability)
    match.next_perk_id += 1
    match.players[player_index].perks.append(instance)
    return instance


def offer(match: Match) -> list[str]:
    """DRAFT_SIZE different ready perks, rarer ones less often."""
    pool = [s.id for s in CATALOG.values() if s.ready]
    picked: list[str] = []
    while pool and len(picked) < DRAFT_SIZE:
        weights = [RARITY_WEIGHTS[spec(p).rarity] for p in pool]
        choice = match.rng.choices(pool, weights)[0]
        picked.append(choice)
        pool.remove(choice)
    return picked


def reroll(match: Match, player_index: int) -> None:
    player = match.players[player_index]
    if not player.draft:
        raise ValueError("There's no perk draft to reroll.")
    if player.rerolls_left == 0:
        raise ValueError("No rerolls left this match.")
    player.rerolls_left -= 1
    player.draft = offer(match)
    match.log.append(f"{match.names[player_index]} rerolled the perk draft")


def take(match: Match, player_index: int, perk_ids: list[str]) -> None:
    """Keep one of the offered perks, or none. The turn ends after this."""
    player = match.players[player_index]
    if not player.draft:
        raise ValueError("There's no perk draft to pick from.")
    if not isinstance(perk_ids, list) or len(perk_ids) > 1:
        raise ValueError("Pick one perk, or none to skip.")
    if perk_ids and perk_ids[0] not in player.draft:
        raise ValueError("That perk wasn't offered.")
    player.draft = []
    if perk_ids:  # skipping isn't logged: the next turn starting says enough
        grant(match, player_index, perk_ids[0])
        match.log.append(f"{match.names[player_index]} took {spec(perk_ids[0]).name}")


def fits(perk_id: str, glyph: Glyph) -> bool:
    return glyph.effect_type in TARGET_EFFECTS[spec(perk_id).target]


def apply(match: Match, player_index: int, instance_id: int, position: int) -> bool:
    """Apply one of your perks to a glyph in your hand, before casting.

    Returns whether it did something; a perk that doesn't apply (-ING- on an ING
    glyph, the same bonus twice) changes nothing and keeps its durability.
    """
    if match.winner is not None:
        raise ValueError("Match is already over.")
    if player_index != match.active_player_index:
        raise ValueError("It's not your turn.")
    player = match.players[player_index]
    if player.draft:
        raise ValueError("You already cast this turn: pick a perk or skip.")
    instance = next((p for p in player.perks if p.id == instance_id), None)
    if type(instance_id) is not int or instance is None:
        raise ValueError("You don't have that perk.")
    if type(position) is not int or not 0 <= position < len(player.hand):
        raise ValueError("The glyph position is out of bounds.")
    glyph = player.hand[position]
    perk = spec(instance.perk_id)
    if not fits(perk.id, glyph):
        raise ValueError(f"{perk.name} can't go on a {glyph.effect_type} glyph.")

    if perk.id in BONUS:
        # weak and vulnerable values are turns, so a bonus would do nothing
        applied = not is_status(glyph) and glyph.bonus != perk.id
        if applied:
            glyph.bonus = perk.id  # one slot: a new bonus replaces the old one
    else:
        applied = DIRECT[perk.id](
            glyph, PerkContext(match, player_index, instance.uses)
        )

    name = match.names[player_index]
    if not applied:
        match.log.append(f"{name}'s {perk.name} had no effect")
        return False
    instance.uses += 1
    if instance.durability is not None:
        instance.durability -= 1
    match.log.append(f"{name} used {perk.name} on {glyph.letter}")
    if instance.durability == 0:
        player.perks.remove(instance)
        match.log.append(f"{name}'s {perk.name} broke")
    return True
