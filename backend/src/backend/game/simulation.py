"""Simulated matches: a random bot plays both sides through `apply`, and the
state is checked after every action.

    report = simulate(load_word_list_words, matches=1000)

Every match is seeded ("sim-0", "sim-1", ...), so a failure names a seed
that replays exactly. The bot only makes legal moves, so an ACTION_REJECTED
is reported as a failure too.

Invariants checked after every action:
- no glyph appears or disappears (Erase is the only thing that removes one),
  and no glyph is in two places;
- HP between 0 and max_hp, Defense and clocks not negative;
- no perk at or below 0 durability (a perk at 0 is destroyed);
- statuses have turns left;
- an ended match has a winner and a reason, a running one has neither;
- the turn number only moves forward;
- every match ends within `max_actions`.
"""

import statistics
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import combinations

from backend.game.clock import deadline_ms
from backend.game.conditions import WordContext
from backend.game.config import DEFAULT_CONFIG, STATUS_EFFECTS, Effect, GameConfig
from backend.game.perks import (
    PerkContext,
    PerkKind,
    PerkSpec,
    conditional_rules,
    load_catalog,
    registered,
)
from backend.game.piles import new_match
from backend.game.rng import Rng, rng_for
from backend.game.state import EndReason, Glyph, MatchState, Phase
from backend.game.turns import (
    Action,
    ActionType,
    Event,
    EventType,
    MatchRules,
    apply,
    check_timeout,
    forfeit,
)

USERS = ("sim-player-0", "sim-player-1")


class InvariantError(AssertionError):
    """The engine broke a rule. The message names the seed and the action."""


class WordFinder:
    """Finds the words a hand can spell, using an index of the word list by
    its letters (an anagram index)."""

    def __init__(self, words: Iterable[str]) -> None:
        self._index: dict[str, list[str]] = {}
        for word in words:
            word = word.upper()
            self._index.setdefault("".join(sorted(word)), []).append(word)
        self.words = frozenset(w for ws in self._index.values() for w in ws)

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and word.upper() in self.words

    def plays(self, hand: Sequence[Glyph], max_glyphs: int = 7) -> list[list[int]]:
        """Every (word, glyph order) the hand can play, as hand positions."""
        found: list[list[int]] = []
        for size in range(1, min(len(hand), max_glyphs) + 1):
            for subset in combinations(range(len(hand)), size):
                key = "".join(sorted("".join(hand[i].letters for i in subset)))
                for word in self._index.get(key, ()):
                    order = _spell_order(word, [(i, hand[i].letters) for i in subset])
                    if order is not None:
                        found.append(order)
        return found


def _spell_order(word: str, pieces: list[tuple[int, str]]) -> list[int] | None:
    """Arrange glyphs (position, letters) so their letters spell `word`."""
    if not word:
        return [] if not pieces else None
    for k, (position, letters) in enumerate(pieces):
        if word.startswith(letters):
            rest = _spell_order(word[len(letters) :], pieces[:k] + pieces[k + 1 :])
            if rest is not None:
                return [position, *rest]
    return None


@dataclass(frozen=True, slots=True)
class BotStyle:
    """How the bot plays. Times are in milliseconds, drawn evenly from each
    range; the defaults are a guess at an ordinary human player."""

    cast_ms: tuple[int, int] = (4_000, 20_000)
    perk_ms: tuple[int, int] = (1_500, 5_000)
    draft_ms: tuple[int, int] = (2_000, 8_000)
    # Pick among this many best-scoring words; None picks any word at random.
    choose_from_best: int | None = 5
    # Pass when the hand spells nothing; False waits for the clock instead.
    pass_when_stuck: bool = True
    # Choose the word first and use perks where they pay off; False applies
    # perks to random glyphs.
    smart_perks: bool = True
    perk_chance: float = 0.5
    max_perks_per_turn: int = 2
    reroll_chance: float = 0.2
    resign_chance: float = 0.0
    disconnect_chance: float = 0.0


@dataclass(slots=True)
class MatchSummary:
    seed: str
    first_player: int
    winner: int | None
    end_reason: EndReason | None
    turns: int
    actions: int
    words: list[str] = field(default_factory=list)
    perks_applied: int = 0
    glyphs_erased: int = 0
    turns_without_a_word: int = 0
    seconds_used: list[float] = field(default_factory=list)


@dataclass(slots=True)
class SimulationReport:
    matches: list[MatchSummary]

    @property
    def first_player_win_rate(self) -> float:
        decided = [m for m in self.matches if m.winner is not None]
        if not decided:
            return 0.0
        return sum(m.winner == m.first_player for m in decided) / len(decided)

    def summary(self) -> dict[str, object]:
        turns = [m.turns for m in self.matches]
        words = [w for m in self.matches for w in m.words]
        return {
            "matches": len(self.matches),
            "turns_mean": round(statistics.mean(turns), 1),
            "turns_median": statistics.median(turns),
            "turns_min": min(turns),
            "turns_max": max(turns),
            "first_player_win_rate": round(self.first_player_win_rate, 3),
            "end_reasons": dict(
                Counter(m.end_reason.value for m in self.matches if m.end_reason)
            ),
            "words_cast": len(words),
            "word_length_mean": round(statistics.mean(map(len, words)), 2)
            if words
            else 0,
            "perks_applied": sum(m.perks_applied for m in self.matches),
            "glyphs_erased": sum(m.glyphs_erased for m in self.matches),
            "turns_passed_or_stuck": sum(m.turns_without_a_word for m in self.matches),
            "timeout_share": round(
                sum(m.end_reason == EndReason.TIMEOUT for m in self.matches)
                / len(self.matches),
                3,
            ),
        }


class _Run:
    def __init__(
        self,
        seed: str,
        finder: WordFinder,
        rules: MatchRules,
        style: BotStyle,
        time_control: int,
    ) -> None:
        self.seed = seed
        self.finder = finder
        self.rules = rules
        self.config = rules.config
        self.style = style
        self.catalog = rules.perk_catalog()
        self.definitions = registered()
        self.rules_by_perk = conditional_rules()
        self.plan: list[str] | None = None
        self.state = new_match(
            f"match-{seed}", USERS, time_control, seed=seed, config=rules.config
        )
        self.now = 0
        self.actions = 0
        self.erased = [0, 0]
        self.deck_size = [len(p.all_glyphs()) for p in self.state.players]
        self.summary = MatchSummary(
            seed=seed,
            first_player=self.state.active_player,
            winner=None,
            end_reason=None,
            turns=0,
            actions=0,
        )

    def rng(self, purpose: str) -> Rng:
        return rng_for(self.seed, self.actions, f"bot:{purpose}")

    def fail(self, message: str) -> InvariantError:
        return InvariantError(f"seed {self.seed!r}, action {self.actions}: {message}")

    def think(self, purpose: str) -> None:
        style = self.style
        low, high = {
            "cast": style.cast_ms,
            "pass": style.cast_ms,
            "reroll": style.draft_ms,
            "select": style.draft_ms,
        }.get(purpose, style.perk_ms)
        self.now += self.rng(f"think:{purpose}").randint(low, high)

    def score(
        self, player: int, play: list[int], hand: Sequence[Glyph] | None = None
    ) -> float:
        """Roughly how good a word is, the way a decent player would judge."""
        side = self.state.player(player)
        opponent = self.state.player(1 - player)
        hand = side.hand if hand is None else hand
        glyphs = tuple(hand[i] for i in play)
        word = "".join(g.letters for g in glyphs)
        total = 0.0
        for index, position in enumerate(play):
            glyph = hand[position]
            value = glyph.value
            rule = self.rules_by_perk.get(glyph.conditional_slot or "")
            if rule is not None and glyph.effect not in STATUS_EFFECTS:
                context = WordContext(
                    word, glyphs, index, side.hp, opponent.hp, self.config.max_hp
                )
                value = rule(glyph, context, value)
            glyph = replace(glyph, value=value)
            if glyph.effect == Effect.DAMAGE:
                total += glyph.value
            elif glyph.effect == Effect.DEFENSE:
                total += glyph.value * 0.6
            elif glyph.effect == Effect.HEAL:
                total += glyph.value * 0.6 if side.hp < self.config.max_hp else 0
            else:
                total += glyph.value * 4
        return total

    def send(self, player: int, kind: ActionType, **data: object) -> list[Event]:
        before_turn = self.state.turn
        self.state, events = apply(
            self.state, Action(player, kind, data), self.now, self.rules
        )
        self.after(events, before_turn)
        return events

    def after(self, events: list[Event], before_turn: int) -> None:
        self.actions += 1
        for event in events:
            if event.type == EventType.ACTION_REJECTED:
                raise self.fail(f"legal move rejected: {event.data}")
            if event.type == EventType.PERK_APPLIED:
                self.summary.perks_applied += int(bool(event.data["applied"]))
                if event.data["glyph"] is None:
                    self.erased[event.data["player"]] += 1
                    self.summary.glyphs_erased += 1
            if event.type == EventType.WORD_RESOLVED:
                self.summary.words.append(event.data["word"])
        self.check(before_turn)

    def check(self, before_turn: int) -> None:
        state, config = self.state, self.config
        if state.turn < before_turn:
            raise self.fail("the turn number went back")
        for index, side in enumerate(state.players):
            glyphs = side.all_glyphs()
            if len(glyphs) + self.erased[index] != self.deck_size[index]:
                raise self.fail(f"player {index} has {len(glyphs)} glyphs")
            if len({g.id for g in glyphs}) != len(glyphs):
                raise self.fail(f"player {index} has a glyph in two places")
            if not 0 <= side.hp <= config.max_hp:
                raise self.fail(f"player {index} HP is {side.hp}")
            if side.defense < 0 or side.clock_ms < 0:
                raise self.fail(f"player {index} defense/clock below 0")
            if side.clock_ms > state.time_control_seconds * 1000:
                raise self.fail(f"player {index} clock above the time control")
            for perk in side.perks:
                if perk.durability is not None and perk.durability <= 0:
                    raise self.fail(f"perk {perk.instance_id} at {perk.durability}")
            if any(s.turns_left <= 0 for s in side.statuses):
                raise self.fail(f"player {index} has an expired status")
            if index != state.active_player and side.hand:
                raise self.fail(f"waiting player {index} holds a hand")
        ended = state.phase == Phase.ENDED
        if ended != (state.winner is not None) or ended != (
            state.end_reason is not None
        ):
            raise self.fail("winner/end reason don't match the phase")
        if (
            state.winner is not None
            and state.end_reason == EndReason.HEALTH_DEPLETED
            and state.players[1 - state.winner].hp != 0
        ):
            raise self.fail("HEALTH_DEPLETED but the loser has HP")

    # One bot decision -------------------------------------------------------

    def ready(self) -> None:
        for player in (0, 1):
            self.think("ready")
            self.send(player, ActionType.PLAYER_READY)

    def maybe_forfeit(self, player: int) -> bool:
        rng = self.rng("forfeit")
        roll = rng.random()
        style = self.style
        if roll < style.resign_chance:
            reason = EndReason.RESIGNATION
        elif roll < style.resign_chance + style.disconnect_chance:
            reason = EndReason.DISCONNECT
        else:
            return False
        before = self.state.turn
        self.state, events = forfeit(self.state, player, reason, self.now)
        self.after(events, before)
        return True

    def apply_perks(self, player: int) -> None:
        if self.style.smart_perks:
            self.apply_perks_smartly(player)
            return
        rng = self.rng("perks")
        for _ in range(self.style.max_perks_per_turn):
            side = self.state.player(player)
            if (
                not side.perks
                or not side.hand
                or rng.random() >= self.style.perk_chance
            ):
                return
            perk = rng.choice(side.perks)
            spec = self.catalog[perk.perk_id]
            targets = [i for i, g in enumerate(side.hand) if spec.supports(g.type)]
            if not targets:
                continue
            self.think("perk")
            self.send(
                player,
                ActionType.APPLY_PERK,
                turn=self.state.turn,
                glyph_index=rng.choice(targets),
                perk_instance_id=perk.instance_id,
            )
            if self.state.phase != Phase.ACTION:
                return

    # Smart perk use: pick the word first, then use perks where they pay off.

    def best_plays(self, player: int, hand: Sequence[Glyph]) -> list[list[int]]:
        plays = self.finder.plays(hand)
        plays.sort(key=lambda play: self.score(player, play, hand), reverse=True)
        best = self.style.choose_from_best
        return plays if best is None else plays[:best]

    def plan_word(self, player: int) -> list[str] | None:
        """Choose a word; returns the glyph ids that spell it."""
        side = self.state.player(player)
        hand = side.hand
        plays = self.finder.plays(hand)
        if not plays:
            return None
        plays.sort(key=lambda play: self.score(player, play, hand), reverse=True)
        slot_perks = {
            p.perk_id for p in side.perks if self.definitions[p.perk_id].condition
        }

        def with_perks(play: list[int]) -> float:
            gains = sorted(
                (self.evaluate(player, perk_id, play)[0] for perk_id in slot_perks),
                reverse=True,
            )
            bonus = sum(gains[: self.style.max_perks_per_turn])
            return self.score(player, play, hand) + bonus

        candidates = plays[:30]
        candidates.sort(key=with_perks, reverse=True)
        best = self.style.choose_from_best or len(candidates)
        return [hand[i].id for i in self.rng("plan").choice(candidates[:best])]

    def plan_positions(self, player: int, plan: list[str] | None) -> list[int] | None:
        if plan is None:
            return None
        ids = [g.id for g in self.state.player(player).hand]
        if not all(glyph_id in ids for glyph_id in plan):
            return None
        positions = [ids.index(glyph_id) for glyph_id in plan]
        word = "".join(self.state.player(player).hand[i].letters for i in positions)
        return positions if word in self.finder else None

    def trial(self, player: int, perk_id: str, position: int) -> Glyph | None:
        """The glyph after a direct perk, tried on a copy; None if it wouldn't
        apply."""
        definition = self.definitions[perk_id]
        assert definition.apply is not None
        scratch = MatchState.from_dict(self.state.to_dict())
        glyph = scratch.player(player).hand[position]
        context = PerkContext(scratch, player, self.rng("trial"), self.config)
        return glyph if definition.apply(glyph, context) else None

    def evaluate(
        self, player: int, perk_id: str, plan: list[int] | None
    ) -> tuple[float, int | None]:
        """(estimated gain, glyph position) for using a perk now; gain 0
        means not worth it."""
        side = self.state.player(player)
        opponent = self.state.player(1 - player)
        hand = side.hand
        spec = self.catalog[perk_id]
        definition = self.definitions[perk_id]
        usable = [
            i
            for i, g in enumerate(hand)
            if spec.supports(g.type) and g.conditional_slot != perk_id
        ]
        in_word = [i for i in usable if plan is not None and i in plan]
        spare = [i for i in usable if plan is None or i not in plan]
        nothing: tuple[float, int | None] = (0.0, None)
        if not usable:
            return nothing

        if definition.condition is not None:
            if plan is None:
                return nothing
            glyphs = tuple(hand[i] for i in plan)
            word = "".join(g.letters for g in glyphs)
            best: tuple[float, int | None] = nothing
            for index, position in enumerate(plan):
                glyph = hand[position]
                if position not in usable or glyph.effect in STATUS_EFFECTS:
                    continue
                context = WordContext(
                    word, glyphs, index, side.hp, opponent.hp, self.config.max_hp
                )
                extra = definition.condition(glyph, context, glyph.value) - glyph.value
                if extra > best[0]:
                    best = (float(extra), position)
            return best

        if definition.kind == PerkKind.DECK:
            if perk_id == "erase":
                # Thin the deck of weak glyphs the word doesn't need.
                weak = [i for i in spare if hand[i].value <= 7]
                return (2.5, weak[0]) if weak else nothing
            # Redraw and Fresh Start: when the hand spells nothing; Redraw also
            # swaps a spare glyph when the best word is short.
            if plan is None:
                return (5.0, usable[0])
            weak_hand = self.score(player, plan, hand) < 15
            if perk_id == "fresh_start":
                return (4.0, usable[0]) if weak_hand else nothing
            if len(plan) <= 4 and spare:
                return (2.0, min(spare, key=lambda i: hand[i].value))
            return nothing

        current = self.score(player, plan, hand) if plan is not None else 0.0
        if definition.kind == PerkKind.LETTERS:
            best = nothing
            for position in usable:
                changed = self.trial(player, perk_id, position)
                if changed is None:
                    continue
                trial_hand = [
                    changed if i == position else g for i, g in enumerate(hand)
                ]
                for play in self.finder.plays(trial_hand):
                    if position in play:
                        gain = self.score(player, play, trial_hand) - current
                        if gain > best[0]:
                            best = (gain, position)
            return best

        if perk_id in ("hex", "expose"):
            effect = Effect.WEAK if perk_id == "hex" else Effect.VULNERABLE
            if any(s.effect == effect for s in opponent.statuses):
                return nothing
            # The glyph is only the target; the status goes on the opponent.
            return (8.0, usable[0])
        if perk_id == "linger":
            return (5.0, usable[0])
        if perk_id == "wild_skill":
            hurt = side.hp * 2 < self.config.max_hp
            return (4.0, in_word[0]) if hurt and in_word else nothing
        if perk_id == "blood" and side.hp <= 20:
            return nothing

        # Value and type perks: the glyph in the word where it adds the most.
        best = nothing
        for position in in_word:
            changed = self.trial(player, perk_id, position)
            if changed is None:
                continue
            trial_hand = [changed if i == position else g for i, g in enumerate(hand)]
            gain = self.score(player, plan or [], trial_hand) - current
            if gain > best[0]:
                best = (gain, position)
        return best

    def apply_perks_smartly(self, player: int) -> None:
        self.plan = self.plan_word(player)
        for _ in range(self.style.max_perks_per_turn):
            side = self.state.player(player)
            positions = self.plan_positions(player, self.plan)
            choice = None
            best_gain = 0.0
            for perk in sorted(side.perks, key=lambda p: p.instance_id):
                gain, target = self.evaluate(player, perk.perk_id, positions)
                if target is not None and gain > best_gain:
                    choice, best_gain = (perk.instance_id, target), gain
            if choice is None:
                return
            self.think("perk")
            self.send(
                player,
                ActionType.APPLY_PERK,
                turn=self.state.turn,
                glyph_index=choice[1],
                perk_instance_id=choice[0],
            )
            if self.state.phase != Phase.ACTION:
                return
            if self.plan_positions(player, self.plan) is None:
                self.plan = self.plan_word(player)

    def cast(self, player: int) -> None:
        plays = self.finder.plays(self.state.player(player).hand)
        if not plays and self.style.pass_when_stuck:
            self.summary.turns_without_a_word += 1
            self.think("pass")
            self.send(player, ActionType.PASS_TURN, turn=self.state.turn)
            return
        if not plays:
            # Nothing to spell and no passing: the clock runs out.
            self.summary.turns_without_a_word += 1
            deadline = deadline_ms(self.state)
            assert deadline is not None
            self.now = deadline
            before = self.state.turn
            self.state, events = check_timeout(self.state, self.now)
            if not events:
                raise self.fail("the deadline passed without a timeout")
            self.after(events, before)
            return
        planned = self.plan_positions(player, self.plan)
        if planned is not None and self.style.smart_perks:
            sequence = planned
        else:
            hand = self.state.player(player).hand
            best = self.style.choose_from_best
            if best is not None:
                plays.sort(
                    key=lambda play: self.score(player, play, hand), reverse=True
                )
                plays = plays[:best]
            sequence = self.rng("word").choice(plays)
        self.plan = None
        self.think("cast")
        self.send(
            player,
            ActionType.CAST_WORD,
            turn=self.state.turn,
            glyph_sequence=sequence,
        )

    def draft(self, player: int) -> None:
        rng = self.rng("draft")
        side = self.state.player(player)
        if side.rerolls_left and rng.random() < self.style.reroll_chance:
            self.think("reroll")
            self.send(player, ActionType.REROLL_PERKS, turn=self.state.turn)
            if self.state.phase != Phase.DRAFT:
                return
        offer = self.state.player(player).draft_offer
        count = min(len(offer), self.config.perks_to_select)
        self.think("select")
        self.send(
            player,
            ActionType.SELECT_PERKS,
            turn=self.state.turn,
            perk_ids=rng.sample(offer, count),
        )

    def play(self, max_actions: int) -> MatchSummary:
        self.ready()
        while self.state.phase != Phase.ENDED:
            if self.actions >= max_actions:
                raise self.fail(f"no end after {max_actions} actions")
            player = self.state.active_player
            if self.state.phase == Phase.ACTION:
                if self.maybe_forfeit(self.rng("who").randrange(2)):
                    continue
                self.apply_perks(player)
                if self.state.phase == Phase.ACTION:
                    self.cast(player)
            elif self.state.phase == Phase.DRAFT:
                self.draft(player)
            else:
                raise self.fail(f"stuck in {self.state.phase.value}")
        limit = self.state.time_control_seconds * 1000
        self.summary.seconds_used = [
            (limit - side.clock_ms) / 1000 for side in self.state.players
        ]
        self.summary.winner = self.state.winner
        self.summary.end_reason = self.state.end_reason
        self.summary.turns = self.state.turn
        self.summary.actions = self.actions
        return self.summary


def simulate(
    words: Iterable[str] | WordFinder,
    matches: int = 1000,
    catalog: Mapping[str, PerkSpec] | None = None,
    config: GameConfig = DEFAULT_CONFIG,
    style: BotStyle | None = None,
    seed_prefix: str = "sim",
    max_actions: int = 2_000,
) -> SimulationReport:
    """Play `matches` seeded matches between two random bots.

    `words` is the word list the bot searches (it is also the dictionary the
    engine checks casts against). Raises InvariantError on the first broken
    rule. Time controls rotate through `config.time_controls`.
    """
    style = BotStyle() if style is None else style
    finder = words if isinstance(words, WordFinder) else WordFinder(words)
    rules = MatchRules(
        finder, catalog=load_catalog() if catalog is None else catalog, config=config
    )
    summaries = []
    for n in range(matches):
        time_control = config.time_controls[n % len(config.time_controls)]
        run = _Run(f"{seed_prefix}-{n}", finder, rules, style, time_control)
        summaries.append(run.play(max_actions))
    return SimulationReport(summaries)
