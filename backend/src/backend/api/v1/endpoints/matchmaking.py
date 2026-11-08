from backend.api.dependencies.auth import (
    get_current_user,
    get_redis,
)
from backend.core.dependencies import get_matchmaking_queue
from backend.core.identifiers import user_id_to_string
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.match import MatchRepository
from backend.schemas.matchmaking import (
    CustomMatchCreateRequest,
    CustomMatchResponse,
    JoinMatchRequest,
    MatchPlayerResponse,
    MatchStatusEnum,
    QueueJoinRequest,
    QueueLeaveRequest,
    QueueTicketResponse,
    AIMatchCreateRequest,
    AIMatchResponse,
    AIDifficultyEnum,
)
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from backend.repositories.user import UserRepository

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
    user_id_str = user_id_to_string(current_user.id)
    queue_store = MatchmakingQueueStore(redis)
    ticket = await queue_store.add_to_queue(
        user_id_str, payload.time_control_seconds, current_user.elo
    )

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
    user_id_str = user_id_to_string(current_user.id)
    cancelled = await queue_store.cancel_queue(
        user_id_str, payload.time_control_seconds
    )

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
    user_id_str = user_id_to_string(current_user.id)

    ticket = await queue_store.get_user_ticket(user_id_str)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active matchmaking ticket found.",
        )

    return QueueTicketResponse(**ticket)


@router.post(
    "/matches/custom",
    response_model=CustomMatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a private custom lobby or challenge",
)
async def create_private_match_lobby(
    payload: CustomMatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a pending match lobby in WAITING status with a private 6-character join code.
    """
    match_repo = MatchRepository(db)
    active_match = await match_repo.get_active_match_for_user(current_user.id)
    if active_match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a match while in an active or pending match.",
        )

    match = await match_repo.create_custom_match(
        creator_id_bytes=current_user.id,
        time_control_seconds=payload.time_control_seconds,
    )

    return CustomMatchResponse(
        id=user_id_to_string(match.id),
        invite_code=match.invite_code,
        status=MatchStatusEnum.WAITING,
        time_control_seconds=match.time_control_seconds,
        creator=MatchPlayerResponse(
            id=user_id_to_string(current_user.id),
            username=current_user.username,
            avatar_url=getattr(current_user, "avatar_url", None),
        ),
        created_at=match.created_at,
    )


@router.post(
    "/matches/join",
    response_model=CustomMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Join a custom match lobby using an invite code",
)
async def join_custom_match(
    payload: JoinMatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates an invite code, assigns the joining user as player 2, and starts the match.
    """
    match_repo = MatchRepository(db)

    # 1. Ensure joining player isn't already in an active match
    active_match = await match_repo.get_active_match_for_user(current_user.id)
    if active_match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join a match while in an active or pending match.",
        )

    # 2. Join and activate match
    match = await match_repo.join_match_by_code(
        joiner_id_bytes=current_user.id,
        invite_code=payload.invite_code,
    )

    user_repo = UserRepository(db)
    creator_user = await user_repo.get_user_by_id(match.player1_id)
    username = creator_user.username if creator_user else "Creator"

    return CustomMatchResponse(
        id=user_id_to_string(match.id),
        invite_code=match.invite_code,
        status=MatchStatusEnum(match.status.value),
        time_control_seconds=match.time_control_seconds,
        is_private=match.invite_code is not None,
        creator=MatchPlayerResponse(
            id=user_id_to_string(match.player1_id),
            username=username,
            avatar_url=None,
        ),
        created_at=match.created_at,
    )


@router.post(
    "/matches/ai",
    response_model=AIMatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Instantiate a bot match against AI",
)
async def create_ai_match(
    payload: AIMatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates an active single-player match against an AI bot with specified difficulty.
    """
    match_repo = MatchRepository(db)
    active_match = await match_repo.get_active_match_for_user(current_user.id)
    if active_match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start an AI match while in an active or pending match.",
        )

    match = await match_repo.create_ai_match(
        player_id_bytes=current_user.id,
        ai_difficulty=payload.difficulty.value,
        time_control_seconds=payload.time_control_seconds,
    )

    return AIMatchResponse(
        id=user_id_to_string(match.id),
        is_ai_match=bool(match.is_ai_match),
        ai_difficulty=AIDifficultyEnum(match.ai_difficulty),
        status=MatchStatusEnum.ACTIVE,
        time_control_seconds=match.time_control_seconds,
        player=MatchPlayerResponse(
            id=user_id_to_string(current_user.id),
            username=current_user.username,
            avatar_url=getattr(current_user, "avatar_url", None),
        ),
        created_at=match.created_at,
    )
