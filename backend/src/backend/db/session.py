from collections.abc import AsyncGenerator  # I001

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

engine = None
async_session_maker = None


async def init_db(credentials: dict) -> None:
    global engine, async_session_maker

    database_url = URL.create(
        drivername="mysql+asyncmy",
        username=credentials["username"],
        password=credentials["password"],
        host=credentials["host"],
        port=int(credentials["port"]),
        database=credentials["database"],
        query={"charset": "utf8mb4"},
    )

    engine = create_async_engine(
        database_url,
        echo=False,
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


async def close_db() -> None:
    global engine, async_session_maker

    if engine is not None:
        await engine.dispose()

    engine = None
    async_session_maker = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if async_session_maker is None:
        raise RuntimeError("Database has not been initialized")

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

