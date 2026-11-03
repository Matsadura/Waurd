# app/repositories/user.py
from collections.abc import Sequence

from backend.models.user import User
from backend.repositories.base import BaseRepository
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

# from sqlalchemy.orm import selectinload


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_one_or_none(User.email == email)

    async def get_by_username(self, username: str) -> User | None:
        return await self.get_one_or_none(User.username == username)

    async def search_online_by_query(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[User]:
        pattern = f"%{query}%"
        return await self.list(
            User.is_online.is_(True),
            or_(User.email.ilike(pattern)),
            order_by=[User.created_at.desc()],
            limit=limit,
            offset=offset,
        )
