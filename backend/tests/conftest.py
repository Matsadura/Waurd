"""Shared fixtures for the API test suite.

The suite exercises the real FastAPI app over ASGI. Only the infrastructure is
swapped out: MySQL becomes a throwaway SQLite file per test and Redis becomes
fakeredis, so no running services are needed.
"""

import os

# Must happen before anything imports backend.core.config. Environment variables
# take precedence over a developer's local .env, and the unresolvable DB host
# guarantees the suite can never reach a real database.
os.environ.update(
    ENVIRONMENT="test",
    API_V1_STR="/api/v1",
    DB_HOST="db.invalid",
    REDIS_URL="redis://redis.invalid:6379/0",
    SESSION_COOKIE_NAME="session_id",
    CSRF_COOKIE_NAME="csrf_token",
    COOKIE_SECURE="false",
    SESSION_TTL_SECONDS="604800",
    SESSION_COOKIE_SAMESITE="lax",
    CORS_ORIGINS='["http://localhost:3000"]',
    GOOGLE_CLIENT_ID="",
    GOOGLE_CLIENT_SECRET="",
)

import itertools
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path
from typing import Any

import fakeredis
import httpx
import pytest
from sqlalchemy import BigInteger, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import NullPool

from backend.core.security import hash_password
from backend.db import uow as uow_module
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import app
from backend.models import Friendship, FriendshipStatus, User

PASSWORD = "SecureP@ssw0rd!123"
# Argon2 is deliberately slow, so seeded users share one precomputed hash.
PASSWORD_HASH = hash_password(PASSWORD)

BASE_URL = "http://testserver/api/v1"
HEALTH_URL = "http://testserver/health"


@compiles(BigInteger, "sqlite")
def _bigint_as_sqlite_integer(_type: BigInteger, _compiler: Any, **_kw: Any) -> str:
    """SQLite only auto-increments primary keys declared exactly as INTEGER."""
    return "INTEGER"


SessionMaker = async_sessionmaker[AsyncSession]
ClientFactory = Callable[[], httpx.AsyncClient]
MakeUser = Callable[..., Awaitable[User]]
LoginAs = Callable[[User], Awaitable[httpx.AsyncClient]]
MakeFriendship = Callable[[User, User, FriendshipStatus], Awaitable[Friendship]]


@pytest.fixture
async def db_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    # A file (not :memory:) with NullPool gives each session its own connection,
    # which matches how the app's separate get_db and UnitOfWork sessions behave.
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        poolclass=NullPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
        # SQLite ignores foreign keys unless asked; MySQL always enforces them.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
def session_maker(db_engine: AsyncEngine) -> SessionMaker:
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
async def redis() -> AsyncIterator[fakeredis.FakeAsyncRedis]:
    # A dedicated server per test keeps fakeredis' shared state from leaking.
    client = fakeredis.FakeAsyncRedis(
        server=fakeredis.FakeServer(), decode_responses=True
    )
    yield client
    await client.aclose()


@pytest.fixture(autouse=True)
def _wire_app(
    session_maker: SessionMaker,
    redis: fakeredis.FakeAsyncRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Point the app's two database entry points and its Redis client at the fakes."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(uow_module, "async_session_maker", session_maker)
    # ASGITransport does not run the lifespan that normally sets this.
    app.state.redis = redis
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def make_client() -> AsyncIterator[ClientFactory]:
    """Create independent clients, so each simulated browser keeps its own cookies."""
    clients: list[httpx.AsyncClient] = []

    def _make() -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            # Unhandled errors surface as 500s, as a real caller would see them.
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url=BASE_URL,
        )
        clients.append(client)
        return client

    yield _make
    for client in clients:
        await client.aclose()


@pytest.fixture
def client(make_client: ClientFactory) -> httpx.AsyncClient:
    """An anonymous client with no cookies."""
    return make_client()


@pytest.fixture
def anon_with_csrf(make_client: ClientFactory) -> httpx.AsyncClient:
    """A client that passes the CSRF check but has no session."""
    anon = make_client()
    anon.cookies.set("csrf_token", "anon-token")
    anon.headers["X-CSRF-Token"] = "anon-token"
    return anon


@pytest.fixture
def make_user(session_maker: SessionMaker) -> MakeUser:
    """Insert a user directly. All seeded users can log in with PASSWORD."""
    sequence = itertools.count(1)

    async def _make(**overrides: Any) -> User:
        number = next(sequence)
        values = {
            "username": f"user{number}",
            "email": f"user{number}@example.com",
            "password_hash": PASSWORD_HASH,
            **overrides,
        }
        async with session_maker() as session:
            user = User(**values)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

    return _make


@pytest.fixture
def make_friendship(session_maker: SessionMaker) -> MakeFriendship:
    async def _make(
        requester: User,
        addressee: User,
        status: FriendshipStatus,
    ) -> Friendship:
        async with session_maker() as session:
            friendship = Friendship(
                requester_id=requester.id,
                addressee_id=addressee.id,
                status=status,
            )
            session.add(friendship)
            await session.commit()
            await session.refresh(friendship)
        return friendship

    return _make


@pytest.fixture
def login_as(make_client: ClientFactory) -> LoginAs:
    """Log in through the real endpoint and return a client ready for mutations."""

    async def _login(user: User) -> httpx.AsyncClient:
        authed = make_client()
        response = await authed.post(
            "/auth/login",
            json={"email": user.email, "password": PASSWORD},
        )
        assert response.status_code == 200, response.text
        authed.headers["X-CSRF-Token"] = authed.cookies["csrf_token"]
        return authed

    return _login


@pytest.fixture
async def alice(make_user: MakeUser) -> User:
    return await make_user(username="alice", email="alice@example.com")


@pytest.fixture
async def bob(make_user: MakeUser) -> User:
    return await make_user(username="bob", email="bob@example.com")


@pytest.fixture
async def carol(make_user: MakeUser) -> User:
    return await make_user(username="carol", email="carol@example.com")


@pytest.fixture
async def alice_client(login_as: LoginAs, alice: User) -> httpx.AsyncClient:
    return await login_as(alice)


@pytest.fixture
async def bob_client(login_as: LoginAs, bob: User) -> httpx.AsyncClient:
    return await login_as(bob)


@pytest.fixture
async def carol_client(login_as: LoginAs, carol: User) -> httpx.AsyncClient:
    return await login_as(carol)
