from backend.api.dependencies.auth import get_current_user
from backend.core.identifiers import user_id_to_bytes as str_to_bytes
from backend.core.identifiers import user_id_to_string as bytes_to_str
from backend.db.session import get_db
from backend.models.friendship import Friendship, FriendshipStatus
from backend.models.user import User
from backend.repositories.friendship import FriendshipRepository
from backend.repositories.user import UserRepository
from backend.schemas.friendship import (
    FriendListResponse,
    FriendRequestCreate,
    FriendRequestUpdate,
    FriendshipResponse,
    FriendUserResponse,
    PendingRequestsResponse,
    RequestAction,
)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/friends", tags=["Friendships & Social"])


# 1. GET /friends - List all accepted friends
@router.get(
    "",
    response_model=FriendListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all accepted friends",
)
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = FriendshipRepository(db)
    friends = await repo.get_accepted_friends(current_user.id)

    friend_responses = [
        FriendUserResponse(
            id=bytes_to_str(friend.id),
            username=friend.username,
            avatar_url=friend.avatar_url,
            is_online=friend.is_online,
            last_seen_at=friend.last_seen_at,
        )
        for friend in friends
    ]
    return FriendListResponse(friends=friend_responses)


# 2. GET /friends/requests - List pending incoming and outgoing requests
@router.get(
    "/requests",
    response_model=PendingRequestsResponse,
    status_code=status.HTTP_200_OK,
    summary="List pending incoming and outgoing friend requests",
)
async def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = FriendshipRepository(db)
    incoming, outgoing = await repo.get_pending_requests(current_user.id)

    return PendingRequestsResponse(
        incoming=[
            FriendUserResponse(
                id=bytes_to_str(requester.id),
                username=requester.username,
                avatar_url=requester.avatar_url,
                is_online=requester.is_online,
                last_seen_at=requester.last_seen_at,
            )
            for requester in incoming
        ],
        outgoing=[
            FriendUserResponse(
                id=bytes_to_str(addressee.id),
                username=addressee.username,
                avatar_url=addressee.avatar_url,
                is_online=addressee.is_online,
                last_seen_at=addressee.last_seen_at,
            )
            for addressee in outgoing
        ],
    )


# 3. POST /friends/requests - Send a friend request by target_user_id or username
@router.post(
    "/requests",
    response_model=FriendshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a friend request",
)
async def send_friend_request(
    payload: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    target_user: User | None = None

    if payload.target_user_id:
        target_bytes = str_to_bytes(payload.target_user_id)
        target_user = await user_repo.get_by_id(target_bytes)
    elif payload.username:
        target_user = await user_repo.get_by_username(payload.username)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a friend request to yourself",
        )

    friend_repo = FriendshipRepository(db)
    existing = await friend_repo.get_by_users(current_user.id, target_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Friendship relationship already exists with status: {existing.status.value}",
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


# 4. PATCH /friends/requests/{request_id} - Accept or decline an incoming friend request
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
    db: AsyncSession = Depends(get_db),
):
    friend_repo = FriendshipRepository(db)
    friendship = await friend_repo.get_by_id(request_id)

    if not friendship or friendship.addressee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found or not addressed to you",
        )

    if friendship.status != FriendshipStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process request with status: {friendship.status.value}",
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


# 5. DELETE /friends/{friend_id} - Remove an accepted friend
@router.delete(
    "/{friend_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an accepted friend from friend list",
)
async def remove_friend(
    friend_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_bytes = str_to_bytes(friend_id)
    friend_repo = FriendshipRepository(db)
    friendship = await friend_repo.get_by_users(current_user.id, target_bytes)

    if not friendship or friendship.status != FriendshipStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accepted friend relationship not found",
        )

    await friend_repo.delete(friendship)
    return {"detail": "Friend successfully removed"}


# 6. POST /friends/block/{target_user_id} - Block a user
@router.post(
    "/block/{target_user_id}",
    response_model=FriendshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Block a user",
)
async def block_user(
    target_user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_bytes = str_to_bytes(target_user_id)

    if target_bytes == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself",
        )

    friend_repo = FriendshipRepository(db)
    existing = await friend_repo.get_by_users(current_user.id, target_bytes)

    if existing:
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
        requester_id=current_user.id,
        addressee_id=target_bytes,
        status=FriendshipStatus.BLOCKED,
    )

    return FriendshipResponse(
        id=created.id,
        requester_id=bytes_to_str(created.requester_id),
        addressee_id=bytes_to_str(created.addressee_id),
        status=created.status,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


# 7. DELETE /friends/block/{target_user_id} - Unblock a previously blocked user
@router.delete(
    "/block/{target_user_id}",
    status_code=status.HTTP_200_OK,
    summary="Unblock a previously blocked user",
)
async def unblock_user(
    target_user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_bytes = str_to_bytes(target_user_id)
    friend_repo = FriendshipRepository(db)
    existing = await friend_repo.get_by_users(current_user.id, target_bytes)

    if (
        not existing
        or existing.status != FriendshipStatus.BLOCKED
        or existing.requester_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blocked user record not found",
        )

    await friend_repo.delete(existing)
    return {"detail": "User successfully unblocked"}
