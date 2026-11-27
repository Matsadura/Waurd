from backend.models.friendship import Friendship, FriendshipStatus
from backend.models.user import User
from backend.repositories.base import BaseRepository
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


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

    async def get_accepted_friends(
        self, user_id: bytes, skip: int = 0, limit: int = 20
    ) -> tuple[list[User], int]:
        condition = or_(
            Friendship.requester_id == user_id,
            Friendship.addressee_id == user_id,
        ) & (Friendship.status == FriendshipStatus.ACCEPTED)

        count_stmt = select(func.count()).select_from(Friendship).where(condition)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(User)
            .join(
                Friendship,
                or_(
                    (Friendship.requester_id == user_id)
                    & (User.id == Friendship.addressee_id),
                    (Friendship.addressee_id == user_id)
                    & (User.id == Friendship.requester_id),
                ),
            )
            .where(Friendship.status == FriendshipStatus.ACCEPTED)
            .order_by(User.username.asc())
            .offset(skip)
            .limit(limit)
        )
        friends = list((await self.session.execute(stmt)).scalars().all())
        return friends, total

    async def get_pending_requests_by_direction(
        self, user_id: bytes, direction: str, skip: int = 0, limit: int = 20
    ) -> tuple[list[tuple[User, Friendship]], int]:
        """The other player and the request itself, newest first."""
        if direction == "incoming":
            condition = (Friendship.addressee_id == user_id) & (
                Friendship.status == FriendshipStatus.PENDING
            )
            user_join = User.id == Friendship.requester_id
        else:
            condition = (Friendship.requester_id == user_id) & (
                Friendship.status == FriendshipStatus.PENDING
            )
            user_join = User.id == Friendship.addressee_id

        count_stmt = select(func.count()).select_from(Friendship).where(condition)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(User, Friendship)
            .join(Friendship, user_join)
            .where(condition)
            .order_by(Friendship.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = [tuple(row) for row in (await self.session.execute(stmt)).all()]
        return rows, total
