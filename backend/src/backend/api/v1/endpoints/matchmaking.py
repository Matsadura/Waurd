import uuid

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import (
    get_current_user,
    get_redis,
)
from backend.core.dependencies import get_matchmaking_queue
from backend.core.exceptions import (
    BadRequestException,
    EntityNotFoundException,
    ForbiddenException,
)
from backend.core.identifiers import user_id_to_bytes, user_id_to_string
from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.match import MatchRepository, MatchStatus
from backend.repositories.user import UserRepository
from backend.schemas.matchmaking import (
    CustomMatchCreateRequest,
    CustomMatchResponse,
    JoinMatchRequest,
    MatchCastResponse,
    MatchDetailResponse,
    MatchPlayerResponse,
    MatchStatusEnum,
    QueueJoinRequest,
    QueueLeaveRequest,
    QueueStatusEnum,
    QueueTicketResponse,
)

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
        raise BadRequestException(
            "Cannot queue while currently in an active or pending match"
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
        raise EntityNotFoundException("Active matchmaking queue ticket not found")

    return {"detail": "Successfully removed from matchmaking queue"}


@router.get(
    "/status",
    response_model=QueueTicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Poll queue or active match state",
)
async def get_queue_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    queue_store: MatchmakingQueueStore = Depends(get_matchmaking_queue),
):
    user_id_str = user_id_to_string(current_user.id)

    # 1. Check Redis first (user is still waiting in queue)
    ticket = await queue_store.get_user_ticket(user_id_str)
    if ticket:
        return QueueTicketResponse(**ticket)

    # 2. Not in Redis -> check MySQL for an ACTIVE or WAITING match
    match_repo = MatchRepository(db)
    active_match = await match_repo.get_active_match_for_user(current_user.id)
    if active_match:
        status_val = (
            QueueStatusEnum.WAITING
            if active_match.status == MatchStatus.WAITING
            else QueueStatusEnum.MATCHED
        )
        return QueueTicketResponse(
            ticket_id=str(uuid.UUID(bytes=active_match.id)),
            user_id=user_id_str,
            time_control_seconds=active_match.time_control_seconds,
            elo=current_user.elo,
            status=status_val,
            queued_at=active_match.created_at,
            matched_match_id=str(uuid.UUID(bytes=active_match.id)),
        )

    raise EntityNotFoundException("No active matchmaking ticket or match found.")


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
    queue_store: MatchmakingQueueStore = Depends(get_matchmaking_queue),
):
    """
    Creates a pending match lobby in WAITING status with a private 6-character join code.
    """
    match_repo = MatchRepository(db)

    if await queue_store.get_user_ticket(user_id_to_string(current_user.id)):
        raise BadRequestException("Please leave the matchmaking queue first.")
    active_match = await match_repo.get_active_match_for_user(current_user.id)
    if active_match:
        raise BadRequestException(
            "Cannot create a match while in an active or pending match"
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
        is_private=match.invite_code is not None,
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
    queue_store: MatchmakingQueueStore = Depends(get_matchmaking_queue),
):
    """
    Validates an invite code, assigns the joining user as player 2, and starts the match.
    """
    match_repo = MatchRepository(db)
    if await queue_store.get_user_ticket(user_id_to_string(current_user.id)):
        raise BadRequestException("Please leave the matchmaking queue first.")
    # 1. Ensure joining player isn't already in an active match
    active_match = await match_repo.get_active_match_for_user(current_user.id)
    if active_match:
        raise BadRequestException(
            "Cannot join a match while in an active or pending match"
        )

    # 2. Join and activate match
    match = await match_repo.join_match_by_code(
        joiner_id_bytes=current_user.id,
        invite_code=payload.invite_code,
    )

    user_repo = UserRepository(db)
    creator_user = await user_repo.get_by_id(match.player1_id)
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


@router.get(
    "/matches/{match_id}",
    response_model=MatchDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve match details by match ID",
)
async def get_match_details(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches match metadata, participants, final HP, scores, and completion info by match UUID.
    """
    try:
        match_bytes = user_id_to_bytes(match_id)
    except ValueError:
        raise BadRequestException("Invalid match UUID format")

    match_repo = MatchRepository(db)
    user_repo = UserRepository(db)

    match = await match_repo.get_match_by_id(match_bytes)
    if not match:
        raise EntityNotFoundException("Match not found")

    # 1. Fetch Player 1
    p1 = await user_repo.get_by_id(match.player1_id)
    player1_resp = MatchPlayerResponse(
        id=user_id_to_string(match.player1_id),
        username=p1.username if p1 else "Unknown Player",
        avatar_url=getattr(p1, "avatar_url", None) if p1 else None,
    )

    player2_resp: MatchPlayerResponse | None = None
    if match.player2_id:
        p2 = await user_repo.get_by_id(match.player2_id)
        player2_resp = MatchPlayerResponse(
            id=user_id_to_string(match.player2_id),
            username=p2.username if p2 else "Unknown Player",
            avatar_url=getattr(p2, "avatar_url", None) if p2 else None,
        )

    return MatchDetailResponse(
        id=user_id_to_string(match.id),
        invite_code=match.invite_code,
        status=MatchStatusEnum(match.status.value),
        time_control_seconds=match.time_control_seconds,
        player1=player1_resp,
        player2=player2_resp,
        winner_id=user_id_to_string(match.winner_id) if match.winner_id else None,
        end_reason=match.end_reason,
        player1_final_hp=match.player1_final_hp,
        player2_final_hp=match.player2_final_hp,
        total_turns=match.total_turns or 0,
        duration_seconds=match.duration_seconds or 0,
        started_at=match.started_at,
        ended_at=match.ended_at,
        created_at=match.created_at,
    )


@router.get(
    "/matches/{match_id}/casts",
    response_model=list[MatchCastResponse],
    status_code=status.HTTP_200_OK,
    summary="Audit log of all turns cast in a match",
)
async def get_match_casts(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches the turn-by-turn audit log for a match including words played, glyphs, perks, and damage values.
    """
    try:
        match_bytes = user_id_to_bytes(match_id)
    except ValueError:
        raise BadRequestException("Invalid match UUID format")

    match_repo = MatchRepository(db)
    match = await match_repo.get_match_by_id(match_bytes)

    if not match:
        raise EntityNotFoundException("Match not found")

    # Ensure user was either a participant or match is completed/public
    user_bytes = current_user.id
    if (
        match.player1_id != user_bytes
        and match.player2_id != user_bytes
        and match.status == MatchStatus.ACTIVE
    ):
        raise ForbiddenException(
            "Cannot inspect turn logs of an ongoing match you are not participating in"
        )

    casts = await match_repo.get_casts_for_match(match_bytes)

    return [
        MatchCastResponse(
            id=str(cast.id),
            match_id=match_id,
            turn_number=cast.turn_number,
            player_id=user_id_to_string(cast.player_id),
            word_played=cast.word_played,
            glyphs_payload=cast.glyphs_payload or {},
            status_effects_applied=cast.status_effects_applied,
            damage_dealt=cast.damage_dealt,
            defense_gained=cast.defense_gained,
            heal_amount=cast.heal_amount,
            created_at=cast.created_at,
        )
        for cast in casts
    ]


@router.delete(
    "/matches/{match_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel a custom match lobby",
)
async def cancel_custom_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancels a pending WAITING match lobby. Unlocks the host so they can queue or host again.
    """
    try:
        match_bytes = user_id_to_bytes(match_id)
    except ValueError:
        raise BadRequestException("Invalid match UUID format.")

    match_repo = MatchRepository(db)
    await match_repo.cancel_custom_match(
        match_id_bytes=match_bytes,
        user_id_bytes=current_user.id,
    )

    return {"detail": "Match lobby cancelled successfully"}


@router.delete(
    "/matches/{match_id}/abandon",
    status_code=status.HTTP_200_OK,
    summary="Abandon an active match",
)
async def abandon_active_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Abandons an active match. Marks the match as ABANDONED and unlocks the user.
    """
    try:
        match_bytes = user_id_to_bytes(match_id)
    except ValueError:
        raise BadRequestException("Invalid match UUID format.")

    match_repo = MatchRepository(db)
    await match_repo.abandon_active_match(
        match_id_bytes=match_bytes,
        user_id_bytes=current_user.id,
    )

    return {"detail": "Active match abandoned successfully"}
