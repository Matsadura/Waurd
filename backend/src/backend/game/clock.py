"""Chess-style clocks. The engine never reads the time: every call is given
`now_ms` by the runtime (milliseconds from any fixed starting point).

Only the active player's clock runs, during both ACTION and DRAFT. Time is
charged lazily: whenever the engine is called, the active player loses the
time since `MatchState.clock_started_ms`, which then moves to now.
"""

from backend.game.state import JSONDict, MatchState, Phase

RUNNING_PHASES = (Phase.ACTION, Phase.DRAFT)


def is_running(state: MatchState) -> bool:
    return state.phase in RUNNING_PHASES and state.clock_started_ms is not None


def remaining_ms(state: MatchState, player: int, now_ms: int | None = None) -> int:
    """A player's clock at `now_ms` without changing the state. Without
    `now_ms`, the clock as last charged."""
    side = state.player(player)
    if now_ms is None or player != state.active_player or not is_running(state):
        return side.clock_ms
    assert state.clock_started_ms is not None
    elapsed = max(0, now_ms - state.clock_started_ms)
    return max(0, side.clock_ms - elapsed)


def clocks(state: MatchState, now_ms: int | None = None) -> JSONDict:
    """{ user_id: milliseconds left } for both players."""
    return {
        side.user_id: remaining_ms(state, index, now_ms)
        for index, side in enumerate(state.players)
    }


def charge(state: MatchState, now_ms: int) -> bool:
    """Take the time since the clock last started from the active player.
    Returns True if their clock ran out (it is then 0)."""
    if not is_running(state):
        return False
    side = state.player(state.active_player)
    side.clock_ms = remaining_ms(state, state.active_player, now_ms)
    # A clock that went backwards doesn't move the start forward either.
    assert state.clock_started_ms is not None
    state.clock_started_ms = max(state.clock_started_ms, now_ms)
    return side.clock_ms == 0


def deadline_ms(state: MatchState) -> int | None:
    """When the active player's clock runs out if they don't act, so the
    runtime can set a timer and call check_timeout then. None if no clock
    is running."""
    if not is_running(state):
        return None
    assert state.clock_started_ms is not None
    return state.clock_started_ms + state.player(state.active_player).clock_ms
