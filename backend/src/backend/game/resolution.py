"""Resolving a cast word: what each glyph does, in order, and the result.

Glyphs resolve left to right. Each one's value goes through these stages:

1. its value, which already includes changes from perks applied to it
   (perks change the glyph itself when they are applied, for the match);
2. the conditional slot, if a conditional perk fills it;
3. the caster's WEAK, which lowers POWER glyphs;
4. the target's VULNERABLE, which raises DAMAGE.

Then damage, defense and healing are added up and applied, and statuses are
put on the target. The log of every stage is the WORD_RESOLVED payload.

PLACEHOLDER rules, to confirm with the team:
- Percentages round down, glyph by glyph; values never go below 0.
- A VULNERABLE or WEAK glyph's value is a duration in turns, so no stage
  changes it.
- Statuses from a word take effect after that word, not on later glyphs in it.
- Putting on a status the target already has keeps the longer duration.
- The target's Defense absorbs damage before HP does.
"""

import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from backend.game.config import (
    DEFAULT_CONFIG,
    STATUS_EFFECTS,
    Effect,
    GameConfig,
    GlyphType,
)
from backend.game.spelling import selected_glyphs
from backend.game.state import Glyph, JSONDict, MatchState, PlayerState, Status


@dataclass(frozen=True, slots=True)
class WordContext:
    """Where a glyph sits in the cast word, for conditional perks."""

    word: str
    glyphs: tuple[Glyph, ...]
    index: int

    @property
    def is_first(self) -> bool:
        return self.index == 0

    @property
    def is_last(self) -> bool:
        return self.index == len(self.glyphs) - 1


# A conditional perk's check: gets the glyph, its place in the word and its
# value so far, returns the new value (the same value when the condition
# isn't met). Registered under the perk id stored in Glyph.conditional_slot.
ConditionalRule = Callable[[Glyph, WordContext, int], int]


class Stage(enum.StrEnum):
    CONDITIONAL = "CONDITIONAL"
    WEAK = "WEAK"
    VULNERABLE = "VULNERABLE"


@dataclass(frozen=True, slots=True)
class Change:
    """One stage that changed a glyph's value. `perk_id` is set for CONDITIONAL."""

    stage: Stage
    before: int
    after: int
    perk_id: str | None = None

    def to_dict(self) -> JSONDict:
        return {
            "stage": self.stage.value,
            "before": self.before,
            "after": self.after,
            "perk_id": self.perk_id,
        }


@dataclass(frozen=True, slots=True)
class GlyphStep:
    """How one glyph of the word resolved."""

    glyph_id: str
    letters: str
    type: GlyphType
    effect: Effect
    value: int
    changes: tuple[Change, ...]
    final_value: int

    def to_dict(self) -> JSONDict:
        return {
            "glyph_id": self.glyph_id,
            "letters": self.letters,
            "type": self.type.value,
            "effect": self.effect.value,
            "value": self.value,
            "changes": [change.to_dict() for change in self.changes],
            "final_value": self.final_value,
        }


@dataclass(frozen=True, slots=True)
class SideResult:
    """A player's HP, Defense and statuses after the word."""

    hp: int
    defense: int
    statuses: tuple[Status, ...]

    @classmethod
    def of(cls, player: PlayerState) -> "SideResult":
        statuses = tuple(Status(s.effect, s.turns_left) for s in player.statuses)
        return cls(hp=player.hp, defense=player.defense, statuses=statuses)

    def to_dict(self) -> JSONDict:
        return {
            "hp": self.hp,
            "defense": self.defense,
            "statuses": [status.to_dict() for status in self.statuses],
        }


@dataclass(frozen=True, slots=True)
class WordResolution:
    """The result of a cast word. to_dict() is the WORD_RESOLVED payload."""

    caster: int
    target: int
    word: str
    steps: tuple[GlyphStep, ...]
    damage: int
    defense: int
    heal: int
    damage_blocked: int
    hp_damage: int
    hp_healed: int
    statuses_applied: tuple[Status, ...]
    caster_after: SideResult
    target_after: SideResult
    target_defeated: bool = field(default=False)

    def to_dict(self) -> JSONDict:
        return {
            "caster": self.caster,
            "target": self.target,
            "word": self.word,
            "steps": [step.to_dict() for step in self.steps],
            "totals": {
                "damage": self.damage,
                "defense": self.defense,
                "heal": self.heal,
            },
            "damage_blocked": self.damage_blocked,
            "hp_damage": self.hp_damage,
            "hp_healed": self.hp_healed,
            "statuses_applied": [s.to_dict() for s in self.statuses_applied],
            "caster_after": self.caster_after.to_dict(),
            "target_after": self.target_after.to_dict(),
            "target_defeated": self.target_defeated,
        }


def has_status(player: PlayerState, effect: Effect) -> bool:
    return any(s.effect == effect and s.turns_left > 0 for s in player.statuses)


def _percent(value: int, percent: int) -> int:
    return max(0, value * percent // 100)


def _resolve_glyph(
    glyph: Glyph,
    context: WordContext,
    caster: PlayerState,
    target: PlayerState,
    conditionals: Mapping[str, ConditionalRule],
    config: GameConfig,
) -> GlyphStep:
    value = max(0, glyph.value)
    changes: list[Change] = []

    def change(stage: Stage, after: int, perk_id: str | None = None) -> None:
        nonlocal value
        after = max(0, after)
        if after != value:
            changes.append(Change(stage, value, after, perk_id))
            value = after

    if glyph.effect not in STATUS_EFFECTS:
        if glyph.conditional_slot is not None:
            try:
                rule = conditionals[glyph.conditional_slot]
            except KeyError:
                raise ValueError(
                    f"No rule for conditional perk {glyph.conditional_slot!r} "
                    f"on glyph {glyph.id}."
                ) from None
            change(
                Stage.CONDITIONAL, rule(glyph, context, value), glyph.conditional_slot
            )
        if glyph.type == GlyphType.POWER and has_status(caster, Effect.WEAK):
            change(Stage.WEAK, _percent(value, 100 - config.weak_percent))
        if glyph.effect == Effect.DAMAGE and has_status(target, Effect.VULNERABLE):
            change(Stage.VULNERABLE, _percent(value, 100 + config.vulnerable_percent))

    return GlyphStep(
        glyph_id=glyph.id,
        letters=glyph.letters,
        type=glyph.type,
        effect=glyph.effect,
        value=max(0, glyph.value),
        changes=tuple(changes),
        final_value=value,
    )


def _add_status(player: PlayerState, effect: Effect, turns: int) -> None:
    for status in player.statuses:
        if status.effect == effect:
            status.turns_left = max(status.turns_left, turns)
            return
    player.statuses.append(Status(effect, turns))


def resolve_word(
    state: MatchState,
    caster: int,
    positions: Sequence[int],
    conditionals: Mapping[str, ConditionalRule] | None = None,
    config: GameConfig = DEFAULT_CONFIG,
) -> WordResolution:
    """Resolve the glyphs at `positions` in the caster's hand and apply the result.

    Checking the word against the dictionary is validate_cast's job; call it
    first. This changes HP, Defense and statuses in `state` but leaves the
    hand alone: moving the cast glyphs is the turn's job. Raises SpellingError
    for bad positions, and ValueError for a conditional perk with no rule.
    """
    caster_side = state.player(caster)
    target = 1 - caster
    target_side = state.player(target)
    glyphs = tuple(selected_glyphs(caster_side.hand, positions))
    word = "".join(glyph.letters for glyph in glyphs)

    steps = tuple(
        _resolve_glyph(
            glyph,
            WordContext(word, glyphs, index),
            caster_side,
            target_side,
            conditionals or {},
            config,
        )
        for index, glyph in enumerate(glyphs)
    )

    totals = dict.fromkeys(Effect, 0)
    statuses: dict[Effect, int] = {}
    for step in steps:
        if step.effect in STATUS_EFFECTS:
            statuses[step.effect] = max(statuses.get(step.effect, 0), step.final_value)
        else:
            totals[step.effect] += step.final_value

    damage = totals[Effect.DAMAGE]
    damage_blocked = min(damage, target_side.defense)
    target_side.defense -= damage_blocked
    hp_damage = min(damage - damage_blocked, target_side.hp)
    target_side.hp -= hp_damage

    caster_side.defense += totals[Effect.DEFENSE]
    hp_healed = min(totals[Effect.HEAL], max(0, config.max_hp - caster_side.hp))
    caster_side.hp += hp_healed

    for effect, turns in statuses.items():
        _add_status(target_side, effect, turns)

    return WordResolution(
        caster=caster,
        target=target,
        word=word,
        steps=steps,
        damage=damage,
        defense=totals[Effect.DEFENSE],
        heal=totals[Effect.HEAL],
        damage_blocked=damage_blocked,
        hp_damage=hp_damage,
        hp_healed=hp_healed,
        statuses_applied=tuple(Status(e, t) for e, t in statuses.items()),
        caster_after=SideResult.of(caster_side),
        target_after=SideResult.of(target_side),
        target_defeated=target_side.hp == 0,
    )
