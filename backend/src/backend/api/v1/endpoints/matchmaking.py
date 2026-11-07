from backend.api.dependencies.auth import (
    get_current_user,
    get_redis,
)
from backend.core.dependencies import get_matchmaking_queue
from backend.core.identifiers import user_id_to_string as bytes_to_str
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.match import MatchRepository
from backend.schemas.matchmaking import (
    QueueJoinRequest,
    QueueLeaveRequest,
    QueueTicketResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/matchmaking", tags=["Matchmaking & Matches"])


@router.post(
    "/queue",
    response_model=QueueTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join matchmaking queue",
)
async def join_queue(
    payload: QueueJoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Join the matchmaking pool for the selected time control (60s, 180s, 300s).
    """
    # 1. Ensure user is not currently in an active or waiting match in DB
    match_repo = MatchRepository(db)
    active_match = await match_repo.get_active_match_for_user(current_user.id)
    if active_match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
           detail="Cannot queue while currently in an active or pending match.",
        #   detail=f"Userelo: {current_user.elo}",
        )

    # 2. Add user to Redis matchmaking queue
    user_id_str = bytes_to_str(current_user.id)
    queue_store = MatchmakingQueueStore(redis)
    ticket = await queue_store.add_to_queue(user_id_str, payload.time_control_seconds, current_user.elo)

    return QueueTicketResponse(**ticket)

@router.delete(
    "/queue",
    status_code=status.HTTP_200_OK,
    summary="Leave matchmaking pool",
)
async def leave_queue(
    payload: QueueLeaveRequest,
    current_user: User = Depends(get_current_user),
    queue_store: MatchmakingQueueStore = Depends(get_matchmaking_queue),
):
    """Atomically removes user from the matchmaking queue and deletes their ticket."""
    user_id_str = bytes_to_str(current_user.id)
    cancelled = await queue_store.cancel_queue(user_id_str, payload.time_control_seconds)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active matchmaking queue ticket not found.",
        )

    return {"detail": "Successfully removed from matchmaking queue"}

@router.get(
    "/status",
    response_model=QueueTicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Poll queue state as WebSocket fallback",
)
async def get_queue_status(
    current_user: User = Depends(get_current_user),
    queue_store: MatchmakingQueueStore = Depends(get_matchmaking_queue),
):
    """
    Check current matchmaking ticket state, age in queue, and matched match ID.
    Serves as a polling fallback when WebSocket connections drop.
    """
    user_id_str = bytes_to_str(current_user.id)

    ticket = await queue_store.get_user_ticket(user_id_str)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active matchmaking ticket found.",
        )

    return QueueTicketResponse(**ticket)