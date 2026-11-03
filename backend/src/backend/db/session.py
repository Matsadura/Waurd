from collections.abc import AsyncGenerator  # I001

from backend.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI route dependency yielding an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
