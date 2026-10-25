import uuid
from typing import Sequence
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.friendship import Friendship, FriendshipStatus
from backend.models.user import User
from backend.repositories.base import BaseRepository


class FriendshipRepository(BaseRepository[Friendship]):
    def __init__(self, session: AsyncSession):
        super().__init__(Friendship, session)

    async def get_by_users(
        self, user1_bytes: bytes, user2_bytes: bytes
    ) -> Friendship | None:
        """Finds any existing friendship relationship between two users in either direction."""
        stmt = select(Friendship).where(
            or_(
                and_(
                    Friendship.requester_id == user1_bytes,
                    Friendship.addressee_id == user2_bytes,
                ),
                and_(
                    Friendship.requester_id == user2_bytes,
                    Friendship.addressee_id == user1_bytes,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_accepted_friends(self, user_id_bytes: bytes) -> list[User]:
        """Returns all User records who have an ACCEPTED friendship with the user."""
        stmt = select(Friendship).where(
            Friendship.status == FriendshipStatus.ACCEPTED,
            or_(
                Friendship.requester_id == user_id_bytes,
                Friendship.addressee_id == user_id_bytes,
            ),
        )
        result = await self.session.execute(stmt)
        friendships = result.scalars().all()

        friend_ids = [
            f.addressee_id if f.requester_id == user_id_bytes else f.requester_id
            for f in friendships
        ]

        if not friend_ids:
            return []

        users_stmt = select(User).where(User.id.in_(friend_ids))
        users_result = await self.session.execute(users_stmt)
        return list(users_result.scalars().all())

    async def get_pending_requests(
        self, user_id_bytes: bytes
    ) -> tuple[list[User], list[User]]:
        """
        Returns incoming and outgoing pending friend request user lists.
        Tuple: (incoming_request_users, outgoing_request_users)
        """
        # Incoming
        inc_stmt = (
            select(User)
            .join(Friendship, Friendship.requester_id == User.id)
            .where(
                Friendship.addressee_id == user_id_bytes,
                Friendship.status == FriendshipStatus.PENDING,
            )
        )
        inc_res = await self.session.execute(inc_stmt)
        incoming_users = list(inc_res.scalars().all())

        # Outgoing
        out_stmt = (
            select(User)
            .join(Friendship, Friendship.addressee_id == User.id)
            .where(
                Friendship.requester_id == user_id_bytes,
                Friendship.status == FriendshipStatus.PENDING,
            )
        )
        out_res = await self.session.execute(out_stmt)
        outgoing_users = list(out_res.scalars().all())

        return incoming_users, outgoing_users
