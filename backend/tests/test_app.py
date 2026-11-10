"""Tests for app-level behaviour: health check, startup, error handlers and CORS."""

import fakeredis
import pytest
from conftest import HEALTH_URL, PASSWORD
from sqlalchemy.exc import OperationalError

from backend import main as main_module
from backend.db.session import get_db
from backend.main import app, lifespan
from backend.repositories.user import UserRepository


async def raise_connection_error(*_args, **_kwargs):
    raise ConnectionError("secret-internal-host:6379 refused")


@pytest.fixture
def broken_db():
    """Make the health check's database query fail."""

    class BrokenSession:
        execute = staticmethod(raise_connection_error)

    async def override():
        yield BrokenSession()

    app.dependency_overrides[get_db] = override


class TestHealth:
    async def test_healthy(self, client):
        response = await client.get(HEALTH_URL)

        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "services": {
                "database": {"status": "up"},
                "redis": {"status": "up"},
            },
        }

    async def test_database_down(self, client, broken_db):
        response = await client.get(HEALTH_URL)

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["database"] == {
            "status": "down",
            "error": "Database unavailable",
        }
        assert body["services"]["redis"] == {"status": "up"}

    async def test_redis_down(self, client, redis, monkeypatch):
        monkeypatch.setattr(redis, "ping", raise_connection_error)

        response = await client.get(HEALTH_URL)

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["database"] == {"status": "up"}
        assert body["services"]["redis"] == {
            "status": "down",
            "error": "Redis unavailable",
        }

    async def test_failure_details_are_not_leaked(
        self, client, broken_db, redis, monkeypatch
    ):
        monkeypatch.setattr(redis, "ping", raise_connection_error)

        response = await client.get(HEALTH_URL)

        assert response.status_code == 503
        assert "secret-internal-host" not in response.text


class TestLifespan:
    @pytest.fixture
    def startup_redis(self, monkeypatch):
        client = fakeredis.FakeAsyncRedis(server=fakeredis.FakeServer())
        monkeypatch.setattr(main_module.aioredis, "from_url", lambda *_a, **_k: client)
        return client

    async def test_connects_to_redis_on_startup(self, startup_redis):
        async with lifespan(app):
            assert app.state.redis is startup_redis

    async def test_refuses_to_start_without_redis(self, startup_redis, monkeypatch):
        async def failing_ping():
            raise main_module.aioredis.ConnectionError("down")

        monkeypatch.setattr(startup_redis, "ping", failing_ping)

        with pytest.raises(RuntimeError, match="Failed to connect to Redis"):
            async with lifespan(app):
                pass


REGISTER_PAYLOAD = {
    "username": "racer",
    "email": "racer@example.com",
    "password": PASSWORD,
}


class TestDatabaseErrorHandlers:
    @pytest.fixture
    def skip_uniqueness_prechecks(self, monkeypatch):
        """Simulate a concurrent request winning the race after the prechecks."""

        async def not_found(*_args, **_kwargs):
            return None

        monkeypatch.setattr(UserRepository, "get_by_email", not_found)
        monkeypatch.setattr(UserRepository, "get_by_username", not_found)

    async def test_unique_violation_is_a_conflict(
        self, client, alice, skip_uniqueness_prechecks
    ):
        response = await client.post(
            "/auth/register",
            json={**REGISTER_PAYLOAD, "email": alice.email},
        )

        assert response.status_code == 409
        assert response.json() == {"detail": "Username or email already exists."}

    async def test_database_failure_is_generic_500(self, client, monkeypatch):
        async def fail(*_args, **_kwargs):
            raise OperationalError(
                "SELECT secret_column",
                {},
                Exception("connection to secret-host lost"),
            )

        monkeypatch.setattr(UserRepository, "get_by_email", fail)

        response = await client.post("/auth/register", json=REGISTER_PAYLOAD)

        assert response.status_code == 500
        assert response.json() == {"detail": "An internal database operation failed."}


class TestRequestValidationFormat:
    async def test_missing_body_has_a_flat_detail(self, client):
        response = await client.post("/auth/login")

        assert response.status_code == 422
        assert response.json() == {"detail": "Value is required."}

    async def test_malformed_json_has_a_flat_detail(self, client):
        response = await client.post(
            "/auth/login",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)


class TestCors:
    ORIGIN = "http://localhost:3000"

    async def test_preflight_from_allowed_origin(self, client):
        response = await client.options(
            "/auth/login",
            headers={
                "Origin": self.ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-CSRF-Token",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == self.ORIGIN
        assert response.headers["access-control-allow-credentials"] == "true"

    async def test_preflight_from_unknown_origin_is_refused(self, client):
        response = await client.options(
            "/auth/login",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    async def test_simple_response_exposes_csrf_header(self, client):
        response = await client.get(HEALTH_URL, headers={"Origin": self.ORIGIN})

        assert response.headers["access-control-allow-origin"] == self.ORIGIN
        assert response.headers["access-control-expose-headers"] == "X-CSRF-Token"
