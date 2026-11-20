"""The turn state machine: the one entry point the match runtime calls.

    state, events = apply(state, action, now_ms, rules)

A match goes WAITING (until both players send PLAYER_READY), then turn by
turn: ACTION (apply perks, then cast a word or pass), DRAFT (reroll, pick
perks), then the opponent's turn. A cast that brings the target to 0 HP ends
it. PASS_TURN discards the hand without casting, so a hand that spells
nothing doesn't have to wait for the clock; the next turn draws a new one.

Actions and events follow the WebSockets tab of the API spec. Events name
their recipients, because hands and drafts are private: the active player
gets TURN_START with their hand, the other gets OPPONENT_TURN_START with only
its size. The runtime wraps each event in { type, data, seq }.

A bad action (wrong turn number, wrong phase, not your turn, illegal move,
malformed message) returns the state unchanged and one ACTION_REJECTED event
for the sender. `apply` never changes the state it was given; it returns a
new one.

Clocks run on `now_ms` (see clock.py): each call first charges the active
player, and a clock at 0 ends the match with TIMEOUT. The runtime also calls
check_timeout() when deadline_ms() passes, and forfeit() on surrender or when
a disconnected player's grace period runs out.

PLACEHOLDER rules, to confirm with the team:
- After a cast the whole hand is discarded; the next turn draws a new one.
- A status lasting N turns covers the next N turns of the match (both
  players' turns) after the one it was applied in.
- If the draft has nothing to offer, the turn ends right after the cast.
"""

import enum
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.game.clock import RUNNING_PHASES, charge, clocks, is_running
from backend.game.config import DEFAULT_CONFIG, GameConfig
from backend.game.drafting import (
    DraftError,
    DraftOffer,
    open_draft,
    reroll_draft,
    select_perks,
)
from backend.game.perks import PerkError, PerkSpec, apply_perk, load_catalog
from backend.game.piles import discard_hand, draw
from backend.game.resolution import resolve_word
from backend.game.spelling import Dictionary, SpellingError, validate_cast
from backend.game.state import EndReason, JSONDict, MatchState, Phase


class ActionType(enum.StrEnum):
    PLAYER_READY = "PLAYER_READY"
    APPLY_PERK = "APPLY_PERK"
    CAST_WORD = "CAST_WORD"
    REROLL_PERKS = "REROLL_PERKS"
    SELECT_PERKS = "SELECT_PERKS"
    PASS_TURN = "PASS_TURN"


class EventType(enum.StrEnum):
    MATCH_START = "MATCH_START"
    MATCH_STATE = "MATCH_STATE"
    TURN_START = "TURN_START"
    OPPONENT_TURN_START = "OPPONENT_TURN_START"
    PERK_APPLIED = "PERK_APPLIED"
    WORD_RESOLVED = "WORD_RESOLVED"
    PERK_DRAFT_OPTIONS = "PERK_DRAFT_OPTIONS"
    TURN_PASSED = "TURN_PASSED"
    ACTION_REJECTED = "ACTION_REJECTED"
    MATCH_ENDED = "MATCH_ENDED"


class Rejection(enum.StrEnum):
    """ACTION_REJECTED codes. Illegal moves use their own module's problem
    code (SpellingProblem, PerkProblem, DraftProblem)."""

    MALFORMED = "MALFORMED"
    MATCH_ENDED = "MATCH_ENDED"
    NOT_YOUR_TURN = "NOT_YOUR_TURN"
    WRONG_TURN = "WRONG_TURN"
    WRONG_PHASE = "WRONG_PHASE"
    ALREADY_READY = "ALREADY_READY"
    NOT_OFFERED = "NOT_OFFERED"


@dataclass(frozen=True, slots=True)
class Action:
    """A client message for the match. `player` is 0 or 1 (the runtime maps
    the socket's user to it); `data` is the message's payload."""

    player: int
    type: ActionType
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Event:
    """A message to send. `to` holds the player indexes that receive it."""

    type: EventType
    data: JSONDict
    to: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MatchRules:
    """What the engine needs but doesn't load itself."""

    dictionary: Dictionary
    achievement_words: Collection[str] = ()
    catalog: Mapping[str, PerkSpec] | None = None
    config: GameConfig = DEFAULT_CONFIG

    def perk_catalog(self) -> Mapping[str, PerkSpec]:
        return load_catalog() if self.catalog is None else self.catalog


class _Rejected(Exception):
    def __init__(self, code: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


BOTH = (0, 1)


def _draft_event(state: MatchState, offer: DraftOffer) -> Event:
    data = offer.to_dict()
    return Event(
        EventType.PERK_DRAFT_OPTIONS,
        {
            "turn": state.turn,
            "options": data["options"],
            "pick_count": data["picks_required"],
            "rerolls_left": data["rerolls_left"],
        },
        (offer.player,),
    )


def _turn_start_events(state: MatchState) -> list[Event]:
    active = state.active_player
    side = state.player(active)
    return [
        Event(
            EventType.TURN_START,
            {
                "turn": state.turn,
                "hand_glyphs": [glyph.to_dict() for glyph in side.hand],
                "clocks": clocks(state),
            },
            (active,),
        ),
        Event(
            EventType.OPPONENT_TURN_START,
            {
                "turn": state.turn,
                "active_player_id": side.user_id,
                "hand_size": len(side.hand),
                "clocks": clocks(state),
            },
            (1 - active,),
        ),
    ]


def _start_turn(state: MatchState, config: GameConfig) -> list[Event]:
    side = state.player(state.active_player)
    if not config.defense_carries_over:
        side.defense = 0
    draw(state, state.active_player, max(0, config.hand_size - len(side.hand)))
    state.phase = Phase.ACTION
    return _turn_start_events(state)


def _tick_statuses(state: MatchState) -> None:
    for side in state.players:
        for status in side.statuses:
            if status.applied_turn != state.turn:
                status.turns_left -= 1
        side.statuses = [s for s in side.statuses if s.turns_left > 0]


def _end_turn(state: MatchState, config: GameConfig) -> list[Event]:
    discard_hand(state, state.active_player)
    _tick_statuses(state)
    state.active_player = 1 - state.active_player
    state.turn += 1
    return _start_turn(state, config)


def _end_match(state: MatchState, winner: int, reason: EndReason) -> Event:
    state.phase = Phase.ENDED
    state.winner = winner
    state.end_reason = reason
    state.clock_started_ms = None
    for side in state.players:
        side.draft_offer = []
    return Event(
        EventType.MATCH_ENDED,
        {
            "winner_id": state.player(winner).user_id,
            "end_reason": reason.value,
            "p1_hp": state.players[0].hp,
            "p2_hp": state.players[1].hp,
            "clocks": clocks(state),
        },
        BOTH,
    )


def _int(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _Rejected(Rejection.MALFORMED, f"{key} must be a whole number.")
    return value


def _str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise _Rejected(Rejection.MALFORMED, f"{key} must be text.")
    return value


def _list(data: Mapping[str, Any], key: str, item: type) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not all(
        isinstance(x, item) and not isinstance(x, bool) for x in value
    ):
        raise _Rejected(Rejection.MALFORMED, f"{key} must be a list.")
    return value


def _check_turn(state: MatchState, action: Action, phase: Phase) -> None:
    if action.player != state.active_player:
        raise _Rejected(Rejection.NOT_YOUR_TURN, "It's not your turn.")
    if _int(action.data, "turn") != state.turn:
        raise _Rejected(Rejection.WRONG_TURN, f"It is turn {state.turn}.")
    if state.phase != phase:
        raise _Rejected(
            Rejection.WRONG_PHASE, f"That isn't allowed during {state.phase.value}."
        )


def _ready(state: MatchState, action: Action, rules: MatchRules) -> list[Event]:
    if state.phase != Phase.WAITING:
        raise _Rejected(Rejection.WRONG_PHASE, "The match has already started.")
    side = state.player(action.player)
    if side.ready:
        raise _Rejected(Rejection.ALREADY_READY, "You are already ready.")
    side.ready = True
    if not all(player.ready for player in state.players):
        return []
    state.turn = 1
    start = Event(
        EventType.MATCH_START,
        {
            "players": [{"id": p.user_id, "hp": p.hp} for p in state.players],
            "first_player_id": state.player(state.active_player).user_id,
            "clocks": clocks(state),
        },
        BOTH,
    )
    return [start, *_start_turn(state, rules.config)]


def _apply_perk(state: MatchState, action: Action, rules: MatchRules) -> list[Event]:
    _check_turn(state, action, Phase.ACTION)
    index = _int(action.data, "glyph_index")
    instance_id = _str(action.data, "perk_instance_id")
    hand = state.player(action.player).hand
    if not 0 <= index < len(hand):
        raise _Rejected(
            Rejection.MALFORMED, f"Glyph position {index} is not in your hand."
        )
    result = apply_perk(
        state,
        action.player,
        instance_id,
        hand[index].id,
        rules.perk_catalog(),
        rules.config,
    )
    data = result.to_dict()
    data["turn"] = state.turn
    data["perk_instance_id"] = data.pop("instance_id")
    return [Event(EventType.PERK_APPLIED, data, (action.player,))]


def _cast(state: MatchState, action: Action, rules: MatchRules) -> list[Event]:
    _check_turn(state, action, Phase.ACTION)
    positions = _list(action.data, "glyph_sequence", int)
    side = state.player(action.player)
    validate_cast(side.hand, positions, rules.dictionary, rules.achievement_words)
    resolution = resolve_word(state, action.player, positions, config=rules.config)
    discard_hand(state, action.player)

    resolved = resolution.to_dict()
    resolved.update(
        turn=state.turn,
        player_id=side.user_id,
        clocks=clocks(state),
    )
    events = [Event(EventType.WORD_RESOLVED, resolved, BOTH)]

    if resolution.target_defeated:
        events.append(_end_match(state, action.player, EndReason.HEALTH_DEPLETED))
        return events

    offer = open_draft(state, action.player, rules.perk_catalog(), rules.config)
    if not offer.options:
        return events + _end_turn(state, rules.config)
    state.phase = Phase.DRAFT
    return [*events, _draft_event(state, offer)]


def _reroll(state: MatchState, action: Action, rules: MatchRules) -> list[Event]:
    _check_turn(state, action, Phase.DRAFT)
    offer = reroll_draft(state, action.player, rules.perk_catalog(), rules.config)
    return [_draft_event(state, offer)]


def _select(state: MatchState, action: Action, rules: MatchRules) -> list[Event]:
    _check_turn(state, action, Phase.DRAFT)
    perk_ids = _list(action.data, "perk_ids", str)
    offer = state.player(action.player).draft_offer
    picks: list[int] = []
    for perk_id in perk_ids:
        if perk_id not in offer:
            raise _Rejected(Rejection.NOT_OFFERED, f"{perk_id} is not on offer.")
        picks.append(offer.index(perk_id))
    select_perks(state, action.player, picks, rules.perk_catalog(), rules.config)
    return _end_turn(state, rules.config)


def _pass(state: MatchState, action: Action, rules: MatchRules) -> list[Event]:
    """Give up the cast (for example a hand that spells nothing): the hand is
    discarded and the opponent's turn starts. Only before casting."""
    _check_turn(state, action, Phase.ACTION)
    passed = Event(
        EventType.TURN_PASSED,
        {"turn": state.turn, "player_id": state.player(action.player).user_id},
        BOTH,
    )
    return [passed, *_end_turn(state, rules.config)]


_HANDLERS = {
    ActionType.PLAYER_READY: _ready,
    ActionType.APPLY_PERK: _apply_perk,
    ActionType.CAST_WORD: _cast,
    ActionType.REROLL_PERKS: _reroll,
    ActionType.SELECT_PERKS: _select,
    ActionType.PASS_TURN: _pass,
}


def apply(
    state: MatchState, action: Action, now_ms: int, rules: MatchRules
) -> tuple[MatchState, list[Event]]:
    """Apply one player action. Returns the new state and the events to send.

    On a bad action the original state comes back unchanged with a single
    ACTION_REJECTED event for the sender.
    """
    if action.player not in BOTH:
        raise ValueError(f"Player index must be 0 or 1, not {action.player!r}.")
    turn = action.data.get("turn", state.turn)
    try:
        if state.phase == Phase.ENDED:
            raise _Rejected(Rejection.MATCH_ENDED, "The match is over.")
        # Work on a copy, so a rejection halfway through changes nothing.
        new_state = MatchState.from_dict(state.to_dict())
        if charge(new_state, now_ms):
            # Out of time: whatever the action was, the match is over.
            return new_state, [_timeout(new_state)]
        events = _HANDLERS[action.type](new_state, action, rules)
        if is_waiting_to_start(new_state):
            new_state.clock_started_ms = now_ms
    except _Rejected as rejected:
        code, reason = rejected.code, rejected.reason
    except (SpellingError, PerkError, DraftError) as error:
        code, reason = error.problem.value, str(error)
    else:
        return new_state, events
    rejection = Event(
        EventType.ACTION_REJECTED,
        {"action": action.type.value, "turn": turn, "code": code, "reason": reason},
        (action.player,),
    )
    return state, [rejection]


def _timeout(state: MatchState) -> Event:
    return _end_match(state, 1 - state.active_player, EndReason.TIMEOUT)


def is_waiting_to_start(state: MatchState) -> bool:
    """True right after the match started, before its first clock runs."""
    return state.phase in RUNNING_PHASES and state.clock_started_ms is None


def check_timeout(state: MatchState, now_ms: int) -> tuple[MatchState, list[Event]]:
    """End the match with TIMEOUT if the active player's clock has run out
    by `now_ms`. Otherwise the same state comes back with no events."""
    if not is_running(state):
        return state, []
    new_state = MatchState.from_dict(state.to_dict())
    if not charge(new_state, now_ms):
        return state, []
    return new_state, [_timeout(new_state)]


def forfeit(
    state: MatchState, player: int, reason: EndReason, now_ms: int
) -> tuple[MatchState, list[Event]]:
    """`player` gives up (RESIGNATION) or didn't come back (DISCONNECT); the
    other player wins. Works in any phase until the match has ended. If the
    active clock had already run out, the match ends with TIMEOUT instead."""
    if player not in BOTH:
        raise ValueError(f"Player index must be 0 or 1, not {player!r}.")
    if reason not in (EndReason.RESIGNATION, EndReason.DISCONNECT):
        raise ValueError("A forfeit is a RESIGNATION or a DISCONNECT.")
    if state.phase == Phase.ENDED:
        return state, []
    new_state = MatchState.from_dict(state.to_dict())
    if charge(new_state, now_ms):
        return new_state, [_timeout(new_state)]
    return new_state, [_end_match(new_state, 1 - player, reason)]


def match_state(state: MatchState, player: int, now_ms: int | None = None) -> Event:
    """The MATCH_STATE snapshot for one player, sent on every (re)connect.
    The hand and an open draft are included only on that player's own turn.
    With `now_ms`, the clocks show the time left right now."""
    side = state.player(player)
    own_turn = state.active_player == player and state.phase in (
        Phase.ACTION,
        Phase.DRAFT,
    )
    data: JSONDict = {
        "turn": state.turn,
        "phase": state.phase.value,
        "max_hp": DEFAULT_CONFIG.max_hp,
        "active_player_id": state.player(state.active_player).user_id,
        "players": [
            {
                "id": p.user_id,
                "hp": p.hp,
                "defense": p.defense,
                "statuses": [s.to_dict() for s in p.statuses],
                "draw_count": len(p.draw_pile),
                "discard_count": len(p.discard_pile),
                "hand_size": len(p.hand),
                "ready": p.ready,
            }
            for p in state.players
        ],
        "hand": [g.to_dict() for g in side.hand] if own_turn else None,
        "draft_offer": list(side.draft_offer) if own_turn else None,
        "perks": [perk.to_dict() for perk in side.perks],
        "rerolls_left": side.rerolls_left,
        "clocks": clocks(state, now_ms),
        "clock_running_for": (
            state.player(state.active_player).user_id if is_running(state) else None
        ),
        "winner_id": (
            None if state.winner is None else state.player(state.winner).user_id
        ),
        "end_reason": None if state.end_reason is None else state.end_reason.value,
    }
    return Event(EventType.MATCH_STATE, data, (player,))


def parse_action(player: int, message: Mapping[str, Any]) -> Action | None:
    """Turn a socket message { type, data } into an Action, or None if its
    type isn't a match action (chat, ping and surrender are handled
    elsewhere). Payload fields are checked by apply()."""
    kind = message.get("type")
    if not isinstance(kind, str) or kind not in ActionType.__members__:
        return None
    action_type = ActionType(kind)
    data = message.get("data")
    return Action(player, action_type, data if isinstance(data, Mapping) else {})


__all__ = [
    "Action",
    "ActionType",
    "Event",
    "EventType",
    "MatchRules",
    "Rejection",
    "apply",
    "check_timeout",
    "forfeit",
    "is_waiting_to_start",
    "match_state",
    "parse_action",
]
