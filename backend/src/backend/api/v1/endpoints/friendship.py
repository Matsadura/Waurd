from typing import Literal

from backend.api.dependencies.auth import get_current_user
from backend.core.exceptions import (
    BadRequestException,
    EntityNotFoundException,
)
from backend.core.identifiers import parse_user_id
from backend.core.identifiers import user_id_to_string as bytes_to_str
from backend.db.session import get_db
from backend.models.friendship import Friendship, FriendshipStatus
from backend.models.user import User
from backend.repositories.friendship import FriendshipRepository
from backend.repositories.user import UserRepository
from backend.schemas.friendship import (
    FriendRequestCreate,
    FriendRequestUpdate,
    FriendshipResponse,
    FriendUserResponse,
    PendingRequestResponse,
    RequestAction,
)
from backend.schemas.pagination import PaginatedResponse
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/friends", tags=["Friendships & Social"])


def _to_friend_user_response(user: User) -> FriendUserResponse:
    return FriendUserResponse(
        id=bytes_to_str(user.id),
        username=user.username,
        avatar_url=user.avatar_url,
        is_online=user.is_online,
        last_seen_at=user.last_seen_at,
    )


@router.get(
    "",
    response_model=PaginatedResponse[FriendUserResponse],
    status_code=status.HTTP_200_OK,
    summary="List accepted friends",
)
async def get_friends(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Friends per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = FriendshipRepository(db)
    skip = (page - 1) * size
    friends, total = await repo.get_accepted_friends(
        current_user.id, skip=skip, limit=size
    )

    items = [_to_friend_user_response(friend) for friend in friends]
    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.get(
    "/requests",
    response_model=PaginatedResponse[PendingRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List pending incoming or outgoing friend requests",
)
async def get_pending_requests(
    direction: Literal["incoming", "outgoing"] = Query(
        "incoming", description="Filter by incoming or outgoing requests"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Requests per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = FriendshipRepository(db)
    skip = (page - 1) * size
    rows, total = await repo.get_pending_requests_by_direction(
        current_user.id, direction=direction, skip=skip, limit=size
    )

    items = [
        PendingRequestResponse(
            **_to_friend_user_response(user).model_dump(),
            request_id=friendship.id,
            requested_at=friendship.created_at,
        )
        for user, friendship in rows
    ]
    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.post(
    "/requests",
    response_model=FriendshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a friend request",
)
async def send_friend_request(
    payload: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user_repo = UserRepository(db)
    target_user: User | None = None

    if payload.target_user_id:
        target_bytes = parse_user_id(payload.target_user_id)
        target_user = await user_repo.get_by_id(target_bytes)
    elif payload.username:
        target_user = await user_repo.get_by_username(payload.username)

    if not target_user:
        raise EntityNotFoundException("Target user not found")

    if target_user.id == current_user.id:
        raise BadRequestException("Cannot send a friend request to yourself")

    friend_repo = FriendshipRepository(db)
    existing = await friend_repo.get_by_users(current_user.id, target_user.id)
    if existing:
        raise BadRequestException(
            f"Friendship relationship already exists with status: {existing.status.value}"
        )

    friendship_instance = Friendship(
        requester_id=current_user.id,
        addressee_id=target_user.id,
        status=FriendshipStatus.PENDING,
    )
    friendship = await friend_repo.create(friendship_instance)

    return FriendshipResponse(
        id=friendship.id,
        requester_id=bytes_to_str(friendship.requester_id),
        addressee_id=bytes_to_str(friendship.addressee_id),
        status=friendship.status,
        created_at=friendship.created_at,
        updated_at=friendship.updated_at,
    )


@router.patch(
    "/requests/{request_id}",
    response_model=FriendshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept or decline an incoming friend request",
)
async def handle_friend_request(
    request_id: int,
    payload: FriendRequestUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    friend_repo = FriendshipRepository(db)
    friendship = await friend_repo.get_by_id(request_id)

    if not friendship or friendship.addressee_id != current_user.id:
        raise EntityNotFoundException(
            "Friend request not found or not addressed to you"
        )

    if friendship.status != FriendshipStatus.PENDING:
        raise BadRequestException(
            f"Cannot process request with status: {friendship.status.value}"
        )

    if payload.action == RequestAction.DECLINE:
        await friend_repo.delete(friendship)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Friend request declined and removed"},
        )

    updated = await friend_repo.update(
        friendship, {"status": FriendshipStatus.ACCEPTED}
    )

    return FriendshipResponse(
        id=updated.id,
        requester_id=bytes_to_str(updated.requester_id),
        addressee_id=bytes_to_str(updated.addressee_id),
        status=updated.status,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete(
    "/requests/{request_id}",
    status_code=status.HTTP_200_OK,
    summary="Withdraw a friend request you sent",
)
async def withdraw_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Only the sender can withdraw, and only while the request is pending;
    the recipient declines with PATCH instead."""
    friend_repo = FriendshipRepository(db)
    friendship = await friend_repo.get_by_id(request_id)

    if (
        not friendship
        or friendship.requester_id != current_user.id
        or friendship.status != FriendshipStatus.PENDING
    ):
        raise EntityNotFoundException("Pending friend request you sent not found")

    await friend_repo.delete(friendship)
    return {"detail": "Friend request withdrawn"}


@router.delete(
    "/{friend_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an accepted friend from friend list",
)
async def remove_friend(
    friend_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    target_bytes = parse_user_id(friend_id)
    friend_repo = FriendshipRepository(db)
    friendship = await friend_repo.get_by_users(current_user.id, target_bytes)

    if not friendship or friendship.status != FriendshipStatus.ACCEPTED:
        raise EntityNotFoundException("Accepted friend relationship not found")

    await friend_repo.delete(friendship)
    return {"detail": "Friend successfully removed"}


@router.post(
    "/block/{target_user_id}",
    response_model=FriendshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Block a user",
)
async def block_user(
    target_user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    target_bytes = parse_user_id(target_user_id)

    if target_bytes == current_user.id:
        raise BadRequestException("Cannot block yourself")

    if not await UserRepository(db).get_by_id(target_bytes):
        raise EntityNotFoundException("Target user not found")

    friend_repo = FriendshipRepository(db)
    existing = await friend_repo.get_by_users(current_user.id, target_bytes)

    if existing:
        if (
            existing.status == FriendshipStatus.BLOCKED
            and existing.requester_id != current_user.id
        ):
            raise BadRequestException("Cannot block this user")

        updated = await friend_repo.update(
            existing,
            {
                "status": FriendshipStatus.BLOCKED,
                "requester_id": current_user.id,
                "addressee_id": target_bytes,
            },
        )
        return FriendshipResponse(
            id=updated.id,
            requester_id=bytes_to_str(updated.requester_id),
            addressee_id=bytes_to_str(updated.addressee_id),
            status=updated.status,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    created = await friend_repo.create(
        Friendship(
            requester_id=current_user.id,
            addressee_id=target_bytes,
            status=FriendshipStatus.BLOCKED,
        )
    )

    return FriendshipResponse(
        id=created.id,
        requester_id=bytes_to_str(created.requester_id),
        addressee_id=bytes_to_str(created.addressee_id),
        status=created.status,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


@router.delete(
    "/block/{target_user_id}",
    status_code=status.HTTP_200_OK,
    summary="Unblock a previously blocked user",
)
async def unblock_user(
    target_user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    target_bytes = parse_user_id(target_user_id)
    friend_repo = FriendshipRepository(db)
    existing = await friend_repo.get_by_users(current_user.id, target_bytes)

    if (
        not existing
        or existing.status != FriendshipStatus.BLOCKED
        or existing.requester_id != current_user.id
    ):
        raise EntityNotFoundException("Blocked user record not found")

    await friend_repo.delete(existing)
    return {"detail": "User successfully unblocked"}
