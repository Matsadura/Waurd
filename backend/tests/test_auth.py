"""Tests for registration, password login, logout and session refresh."""

import uuid

import pytest
from conftest import PASSWORD
from sqlalchemy import select

from backend.core.security import verify_password
from backend.models import OAuthProvider, User

SESSION_TTL = 604800


def register_payload(**overrides):
    return {
        "username": "new_user",
        "email": "new@example.com",
        "password": PASSWORD,
        **overrides,
    }


def set_cookie_header(response, name):
    headers = response.headers.get_list("set-cookie")
    return next(header for header in headers if header.startswith(f"{name}="))


class TestRegister:
    async def test_creates_user_and_returns_public_profile(self, client):
        response = await client.post(
            "/auth/register",
            json=register_payload(avatar_url=None),
        )

        assert response.status_code == 200
        body = response.json()
        uuid.UUID(body["id"])
        assert body["username"] == "new_user"
        assert body["email"] == "new@example.com"
        assert body["avatar_url"] is None
        assert body["created_at"] and body["updated_at"]

    async def test_response_never_exposes_credentials(self, client):
        response = await client.post("/auth/register", json=register_payload())

        assert set(response.json()) == {
            "id",
            "username",
            "email",
            "avatar_url",
            "created_at",
            "updated_at",
        }
        assert PASSWORD not in response.text

    async def test_stores_password_as_hash(self, client, session_maker):
        await client.post("/auth/register", json=register_payload())

        async with session_maker() as session:
            user = await session.scalar(
                select(User).where(User.email == "new@example.com")
            )

        assert user.password_hash != PASSWORD
        assert verify_password(PASSWORD, user.password_hash)
        assert user.oauth_provider == OAuthProvider.LOCAL

    async def test_registered_user_can_log_in(self, client):
        await client.post("/auth/register", json=register_payload())

        response = await client.post(
            "/auth/login",
            json={"email": "new@example.com", "password": PASSWORD},
        )

        assert response.status_code == 200

    async def test_does_not_start_a_session(self, client):
        response = await client.post("/auth/register", json=register_payload())

        assert response.headers.get_list("set-cookie") == []

    async def test_duplicate_email_is_rejected(self, client, alice):
        response = await client.post(
            "/auth/register",
            json=register_payload(email=alice.email),
        )

        assert response.status_code == 409
        assert response.json() == {"detail": "Email already registered."}

    async def test_duplicate_username_is_rejected(self, client, alice):
        response = await client.post(
            "/auth/register",
            json=register_payload(username=alice.username),
        )

        assert response.status_code == 409
        assert response.json() == {"detail": "Username already taken."}

    @pytest.mark.parametrize(
        ("overrides", "detail"),
        [
            ({"username": "ab"}, "Username must be at least 3 characters."),
            ({"username": "a" * 33}, "Username must be at most 32 characters."),
            ({"username": "  ab  "}, "Username must be at least 3 characters."),
            ({"email": "not-an-email"}, "Email must be a valid email address."),
            ({"password": "short"}, "Password must be at least 8 characters."),
            ({"password": "p" * 129}, "Password must be at most 128 characters."),
            ({"username": 123}, "Username is invalid."),
        ],
    )
    async def test_invalid_fields_are_rejected(self, client, overrides, detail):
        response = await client.post(
            "/auth/register",
            json=register_payload(**overrides),
        )

        assert response.status_code == 422
        assert response.json() == {"detail": detail}

    @pytest.mark.parametrize(
        ("field", "detail"),
        [
            ("username", "Username is required."),
            ("email", "Email must be a valid email address."),
            ("password", "Password is required."),
        ],
    )
    async def test_missing_fields_are_rejected(self, client, field, detail):
        payload = register_payload()
        del payload[field]

        response = await client.post("/auth/register", json=payload)

        assert response.status_code == 422
        assert response.json() == {"detail": detail}

    @pytest.mark.parametrize(
        "overrides",
        [
            {"username": "abc"},
            {"username": "a" * 32},
            {"password": "p" * 8},
            {"password": "p" * 128},
        ],
    )
    async def test_length_limits_are_inclusive(self, client, overrides):
        response = await client.post(
            "/auth/register",
            json=register_payload(**overrides),
        )

        assert response.status_code == 200


class TestLogin:
    async def test_returns_the_user(self, client, alice):
        response = await client.post(
            "/auth/login",
            json={"email": alice.email, "password": PASSWORD},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(uuid.UUID(bytes=alice.id))
        assert body["username"] == "alice"
        assert "password_hash" not in body

    async def test_session_cookie_is_http_only(self, client, alice):
        response = await client.post(
            "/auth/login",
            json={"email": alice.email, "password": PASSWORD},
        )

        cookie = set_cookie_header(response, "session_id").lower()
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        assert f"max-age={SESSION_TTL}" in cookie

    async def test_csrf_cookie_is_readable_by_scripts(self, client, alice):
        response = await client.post(
            "/auth/login",
            json={"email": alice.email, "password": PASSWORD},
        )

        cookie = set_cookie_header(response, "csrf_token").lower()
        assert "httponly" not in cookie
        assert "samesite=lax" in cookie

    async def test_session_is_stored_in_redis_with_ttl(self, client, alice, redis):
        await client.post(
            "/auth/login",
            json={"email": alice.email, "password": PASSWORD},
        )

        key = f"session:{client.cookies['session_id']}"
        assert str(uuid.UUID(bytes=alice.id)) in await redis.get(key)
        assert 0 < await redis.ttl(key) <= SESSION_TTL

    async def test_each_login_creates_a_new_session(self, make_client, alice):
        credentials = {"email": alice.email, "password": PASSWORD}
        first, second = make_client(), make_client()

        await first.post("/auth/login", json=credentials)
        await second.post("/auth/login", json=credentials)

        assert first.cookies["session_id"] != second.cookies["session_id"]
        assert first.cookies["csrf_token"] != second.cookies["csrf_token"]

    async def test_email_whitespace_is_ignored(self, client, alice):
        response = await client.post(
            "/auth/login",
            json={"email": f"  {alice.email}  ", "password": PASSWORD},
        )

        assert response.status_code == 200

    async def test_wrong_password_and_unknown_email_are_indistinguishable(
        self, client, alice
    ):
        wrong_password = await client.post(
            "/auth/login",
            json={"email": alice.email, "password": "WrongPassword1!"},
        )
        unknown_email = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": PASSWORD},
        )

        assert wrong_password.status_code == 401
        assert unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()
        assert wrong_password.json() == {"detail": "Invalid email or password"}

    async def test_failed_login_sets_no_cookies(self, client, alice):
        response = await client.post(
            "/auth/login",
            json={"email": alice.email, "password": "WrongPassword1!"},
        )

        assert response.headers.get_list("set-cookie") == []

    async def test_oauth_user_without_password_cannot_log_in(self, client, make_user):
        user = await make_user(
            password_hash=None,
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id="google-1",
        )

        response = await client.post(
            "/auth/login",
            json={"email": user.email, "password": PASSWORD},
        )

        assert response.status_code == 401

    @pytest.mark.parametrize(
        ("payload", "detail"),
        [
            ({"password": PASSWORD}, "Email must be a valid email address."),
            ({"email": "alice@example.com"}, "Password is required."),
            (
                {"email": "bad", "password": PASSWORD},
                "Email must be a valid email address.",
            ),
            (
                {"email": "alice@example.com", "password": "short"},
                "Password must be at least 8 characters.",
            ),
        ],
    )
    async def test_invalid_payload_is_rejected(self, client, payload, detail):
        response = await client.post("/auth/login", json=payload)

        assert response.status_code == 422
        assert response.json() == {"detail": detail}


class TestLogout:
    async def test_revokes_the_session(self, alice_client, redis):
        session_key = f"session:{alice_client.cookies['session_id']}"

        response = await alice_client.post("/auth/logout")

        assert response.status_code == 204
        assert await redis.exists(session_key) == 0

    async def test_clears_both_cookies(self, alice_client):
        await alice_client.post("/auth/logout")

        assert "session_id" not in alice_client.cookies
        assert "csrf_token" not in alice_client.cookies

    async def test_old_cookie_no_longer_authenticates(self, alice_client, make_client):
        stolen = make_client()
        stolen.cookies.set("session_id", alice_client.cookies["session_id"])

        await alice_client.post("/auth/logout")

        response = await stolen.get("/users/me")
        assert response.status_code == 401

    async def test_leaves_other_sessions_active(self, login_as, alice):
        first = await login_as(alice)
        second = await login_as(alice)

        await first.post("/auth/logout")

        response = await second.get("/users/me")
        assert response.status_code == 200

    async def test_without_session_is_a_no_op(self, anon_with_csrf):
        response = await anon_with_csrf.post("/auth/logout")

        assert response.status_code == 204

    async def test_requires_csrf_token(self, alice_client):
        del alice_client.headers["X-CSRF-Token"]

        response = await alice_client.post("/auth/logout")

        assert response.status_code == 403
        assert response.json() == {"detail": "CSRF token missing"}

    async def test_rejects_mismatched_csrf_token(self, alice_client, redis):
        alice_client.headers["X-CSRF-Token"] = "forged"

        response = await alice_client.post("/auth/logout")

        assert response.status_code == 403
        assert response.json() == {"detail": "CSRF validation failed"}
        session_key = f"session:{alice_client.cookies['session_id']}"
        assert await redis.exists(session_key) == 1


class TestRefreshSession:
    async def test_extends_session_ttl(self, alice_client, redis):
        session_key = f"session:{alice_client.cookies['session_id']}"
        await redis.expire(session_key, 10)

        response = await alice_client.post("/auth/refresh-session")

        assert response.status_code == 204
        assert await redis.ttl(session_key) > 10

    async def test_reissues_session_cookie(self, alice_client):
        session_id = alice_client.cookies["session_id"]

        response = await alice_client.post("/auth/refresh-session")

        cookie = set_cookie_header(response, "session_id")
        assert cookie.startswith(f"session_id={session_id};")
        assert f"Max-Age={SESSION_TTL}" in cookie
        assert "httponly" in cookie.lower()

    async def test_without_session_is_unauthorized(self, anon_with_csrf):
        response = await anon_with_csrf.post("/auth/refresh-session")

        assert response.status_code == 401
        assert response.json() == {"detail": "No active session to refresh."}

    async def test_with_expired_session_is_unauthorized(self, alice_client, redis):
        await redis.delete(f"session:{alice_client.cookies['session_id']}")

        response = await alice_client.post("/auth/refresh-session")

        assert response.status_code == 401
        assert response.json() == {"detail": "Session expired or invalid"}

    async def test_requires_csrf_token(self, alice_client):
        del alice_client.headers["X-CSRF-Token"]

        response = await alice_client.post("/auth/refresh-session")

        assert response.status_code == 403
