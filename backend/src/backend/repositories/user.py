# app/repositories/user.py
from collections.abc import Sequence

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import OAuthProvider, User
from backend.repositories.base import BaseRepository

# from sqlalchemy.orm import selectinload


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_one_or_none(User.email == email)

    async def get_by_username(self, username: str) -> User | None:
        return await self.get_one_or_none(User.username == username)

    async def get_by_oauth_id(self, provider_id: str) -> User | None:
        return await self.get_one_or_none(
            User.oauth_provider == OAuthProvider.GOOGLE,
            User.oauth_id == provider_id,
        )

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
