from types import TracebackType

from backend.db.session import async_session_maker
from backend.repositories.user import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    def __init__(self) -> None:
        self.session_factory = async_session_maker
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self.session_factory()
        self.users = UserRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.session is None:
            return

        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()