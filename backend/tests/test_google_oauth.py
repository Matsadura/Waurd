"""Tests for the Google OAuth flow, with Google's HTTP API replaced by a mock."""

from collections.abc import Callable
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import func, select

from backend.api.v1.endpoints import auth as auth_endpoints
from backend.core.config import settings
from backend.models import OAuthProvider, User

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
FRONTEND_URL = "http://frontend.example/"
PROFILE = {
    "sub": "google-subject-123456",
    "email": "gamer.one@gmail.com",
    "email_verified": True,
    "picture": "https://example.com/pic.png",
}


@pytest.fixture(autouse=True)
def google_settings(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "GOOGLE_FRONTEND_REDIRECT_URI", FRONTEND_URL)


@pytest.fixture
def mock_google(monkeypatch) -> Callable[..., list[httpx.Request]]:
    """Replace the endpoint's HTTP client; returns the requests sent to Google."""

    def _install(
        token_response: httpx.Response | Exception | None = None,
        profile_response: httpx.Response | None = None,
    ) -> list[httpx.Request]:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if str(request.url) == TOKEN_URL:
                if isinstance(token_response, Exception):
                    raise token_response
                return token_response or httpx.Response(
                    200, json={"access_token": "google-access-token"}
                )
            assert str(request.url) == USERINFO_URL
            return profile_response or httpx.Response(200, json=PROFILE)

        def client_factory(**kwargs) -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

        # A stand-in namespace: patching httpx.AsyncClient itself would also
        # affect the test client.
        monkeypatch.setattr(
            auth_endpoints,
            "httpx",
            SimpleNamespace(AsyncClient=client_factory, HTTPError=httpx.HTTPError),
        )
        return requests

    return _install


@pytest.fixture
def callback(client):
    """Begin the flow to obtain a valid state, then call the callback with it."""

    async def _callback(**params) -> httpx.Response:
        start = await client.get("/auth/google")
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        return await client.get(
            "/auth/google/callback",
            params={"code": "auth-code", "state": state, **params},
        )

    return _callback


async def count_users(session_maker) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).select_from(User))


class TestGoogleLogin:
    async def test_redirects_to_google_with_expected_params(self, client):
        response = await client.get("/auth/google")

        assert response.status_code == 307
        location = urlparse(response.headers["location"])
        assert location.netloc == "accounts.google.com"
        query = parse_qs(location.query)
        assert query["client_id"] == ["client-id"]
        assert query["redirect_uri"] == [settings.GOOGLE_REDIRECT_URI]
        assert query["response_type"] == ["code"]
        assert query["scope"] == ["openid email profile"]

    async def test_stores_state_in_cookie_and_redis(self, client, redis):
        response = await client.get("/auth/google")

        state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
        assert client.cookies["google_oauth_state"] == state
        assert await redis.exists(f"session:oauth-state:{state}") == 1
        assert 0 < await redis.ttl(f"session:oauth-state:{state}") <= 600
        assert "httponly" in response.headers["set-cookie"].lower()

    async def test_unconfigured_google_is_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)

        response = await client.get("/auth/google")

        assert response.status_code == 503
        assert response.json() == {"detail": "Google authentication is not configured"}


class TestGoogleCallbackState:
    async def test_error_from_google_is_reported(self, client):
        response = await client.get(
            "/auth/google/callback",
            params={"error": "access_denied"},
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Google authentication was cancelled"}

    @pytest.mark.parametrize("missing", ["code", "state"])
    async def test_missing_query_param_is_rejected(self, client, missing):
        start = await client.get("/auth/google")
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        params = {"code": "auth-code", "state": state}
        del params[missing]

        response = await client.get("/auth/google/callback", params=params)

        assert response.status_code == 400

    async def test_missing_state_cookie_is_rejected(self, client):
        response = await client.get(
            "/auth/google/callback",
            params={"code": "auth-code", "state": "whatever"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Invalid or expired Google authentication state"
        }

    async def test_state_issued_to_another_browser_is_rejected(
        self, client, make_client, mock_google, session_maker
    ):
        # Login CSRF: the attacker's state is valid in Redis but is not bound to
        # the victim's cookie.
        mock_google()
        await client.get("/auth/google")
        attacker_start = await make_client().get("/auth/google")
        attacker_state = parse_qs(urlparse(attacker_start.headers["location"]).query)[
            "state"
        ][0]

        response = await client.get(
            "/auth/google/callback",
            params={"code": "auth-code", "state": attacker_state},
        )

        assert response.status_code == 400
        assert await count_users(session_maker) == 0

    async def test_state_expired_from_redis_is_rejected(self, client, redis):
        start = await client.get("/auth/google")
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        await redis.delete(f"session:oauth-state:{state}")

        response = await client.get(
            "/auth/google/callback",
            params={"code": "auth-code", "state": state},
        )

        assert response.status_code == 400

    async def test_state_cannot_be_replayed(self, client, mock_google):
        mock_google()
        start = await client.get("/auth/google")
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        params = {"code": "auth-code", "state": state}
        first = await client.get("/auth/google/callback", params=params)
        assert first.status_code == 303

        client.cookies.set("google_oauth_state", state)
        replay = await client.get("/auth/google/callback", params=params)

        assert replay.status_code == 400


class TestGoogleCallbackSuccess:
    async def test_creates_user_and_redirects_to_frontend(
        self, callback, mock_google, session_maker
    ):
        mock_google()

        response = await callback()

        assert response.status_code == 303
        assert response.headers["location"] == FRONTEND_URL
        async with session_maker() as session:
            user = await session.scalar(select(User))
        assert user.email == PROFILE["email"]
        assert user.oauth_provider == OAuthProvider.GOOGLE
        assert user.oauth_id == PROFILE["sub"]
        assert user.password_hash is None
        assert user.avatar_url == PROFILE["picture"]

    async def test_generated_username_is_sanitized(
        self, callback, mock_google, session_maker
    ):
        mock_google()

        await callback()

        async with session_maker() as session:
            user = await session.scalar(select(User))
        assert user.username == "gamer_one_google-s"

    async def test_generated_username_fits_the_column(
        self, callback, mock_google, session_maker
    ):
        profile = {**PROFILE, "email": f"{'x' * 60}@gmail.com"}
        mock_google(profile_response=httpx.Response(200, json=profile))

        await callback()

        async with session_maker() as session:
            user = await session.scalar(select(User))
        assert len(user.username) <= 32

    async def test_username_collision_gets_a_fresh_suffix(
        self, callback, mock_google, make_user, session_maker
    ):
        taken = await make_user(username="gamer_one_google-s")
        mock_google()

        response = await callback()

        assert response.status_code == 303
        async with session_maker() as session:
            user = await session.scalar(
                select(User).where(User.email == PROFILE["email"])
            )
        assert user.username != taken.username
        assert user.username.startswith("gamer_one_")

    async def test_session_works_after_callback(self, callback, mock_google, client):
        mock_google()

        await callback()

        response = await client.get("/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == PROFILE["email"]
        assert client.cookies["csrf_token"]
        assert "google_oauth_state" not in client.cookies

    async def test_returning_user_is_not_duplicated(
        self, callback, mock_google, make_user, session_maker, client
    ):
        existing = await make_user(
            email=PROFILE["email"],
            password_hash=None,
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id=PROFILE["sub"],
        )
        mock_google()

        response = await callback()

        assert response.status_code == 303
        assert await count_users(session_maker) == 1
        me = await client.get("/users/me")
        assert me.json()["username"] == existing.username

    async def test_exchanges_code_with_client_credentials(self, callback, mock_google):
        requests = mock_google()

        await callback()

        token_request, profile_request = requests
        token_form = parse_qs(token_request.content.decode())
        assert token_form["code"] == ["auth-code"]
        assert token_form["client_secret"] == ["client-secret"]
        assert token_form["grant_type"] == ["authorization_code"]
        assert profile_request.headers["authorization"] == "Bearer google-access-token"


class TestGoogleCallbackFailures:
    async def test_existing_password_account_is_not_hijacked(
        self, callback, mock_google, make_user, session_maker
    ):
        await make_user(email=PROFILE["email"])
        mock_google()

        response = await callback()

        assert response.status_code == 409
        assert "session_id" not in response.headers.get("set-cookie", "")
        assert await count_users(session_maker) == 1

    async def test_token_endpoint_error_is_bad_gateway(self, callback, mock_google):
        mock_google(token_response=httpx.Response(400, json={"error": "invalid_grant"}))

        response = await callback()

        assert response.status_code == 502
        assert response.json() == {"detail": "Could not complete Google authentication"}

    async def test_network_failure_is_bad_gateway(self, callback, mock_google):
        mock_google(token_response=httpx.ConnectError("boom"))

        response = await callback()

        assert response.status_code == 502

    async def test_missing_access_token_is_bad_gateway(self, callback, mock_google):
        mock_google(token_response=httpx.Response(200, json={}))

        response = await callback()

        assert response.status_code == 502
        assert response.json() == {"detail": "Google did not return an access token"}

    async def test_profile_endpoint_error_is_bad_gateway(self, callback, mock_google):
        mock_google(profile_response=httpx.Response(500))

        response = await callback()

        assert response.status_code == 502

    @pytest.mark.parametrize(
        "profile",
        [
            {**PROFILE, "email_verified": False},
            {key: value for key, value in PROFILE.items() if key != "email"},
            {key: value for key, value in PROFILE.items() if key != "sub"},
            {**PROFILE, "sub": 12345},
        ],
        ids=["unverified", "no-email", "no-subject", "non-string-subject"],
    )
    async def test_unusable_profile_is_rejected(
        self, callback, mock_google, session_maker, profile
    ):
        mock_google(profile_response=httpx.Response(200, json=profile))

        response = await callback()

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Google account does not provide a verified email address"
        }
        assert await count_users(session_maker) == 0

    async def test_missing_client_secret_is_unavailable(
        self, callback, mock_google, monkeypatch
    ):
        mock_google()
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", None)

        response = await callback()

        assert response.status_code == 503
