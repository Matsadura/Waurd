"""Tests for two-factor authentication with emailed codes.

Uses the fixtures in tests/conftest.py from the backend API test suite. Email is
replaced by a fake sender that records codes instead of sending them.
"""

from dataclasses import dataclass, field
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

# This suite lives on backend/api-tests, which may not contain the 2FA code
# yet. Skip instead of failing collection until it is merged in.
pytest.importorskip("fastapi_mail", reason="2FA dependencies are not installed")
pytest.importorskip("backend.core.email", reason="2FA is not merged into this branch")

from backend.core.email import EmailSender, get_email_sender
from backend.core.two_factor import (
    TwoFactorAction,
    TwoFactorStore,
    generate_code,
    mask_email,
)
from conftest import PASSWORD
from fastapi_mail.errors import ConnectionErrors

from backend.api.v1.endpoints import auth as auth_endpoints
from backend.core.config import settings
from backend.core.exceptions import BadGatewayException
from backend.main import app
from backend.models import OAuthProvider, User

GOOGLE_PROFILE = {
    "sub": "google-2fa-user",
    "email": "google2fa@gmail.com",
    "email_verified": True,
}


@dataclass
class SentEmail:
    recipient: str
    code: str
    purpose: str


@dataclass
class FakeSender:
    sent: list[SentEmail] = field(default_factory=list)
    fail: bool = False

    async def send_code(self, recipient, code, purpose):
        if self.fail:
            raise BadGatewayException("Could not send the verification email")
        self.sent.append(SentEmail(recipient, code, getattr(purpose, "value", purpose)))

    @property
    def last_code(self) -> str:
        return self.sent[-1].code


def wrong(code: str) -> str:
    return f"{(int(code) + 1) % 1_000_000:06d}"


async def stored_user(session_maker, user: User) -> User:
    async with session_maker() as session:
        return await session.get(User, user.id)


@pytest.fixture(autouse=True)
def mail() -> FakeSender:
    sender = FakeSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    return sender


@pytest.fixture
async def secured(make_user) -> User:
    """A password user with 2FA already enabled."""
    return await make_user(
        username="secured",
        email="secured@example.com",
        two_factor_enabled=True,
    )


async def password_login(client: httpx.AsyncClient, user: User) -> httpx.Response:
    return await client.post(
        "/auth/login",
        json={"email": user.email, "password": PASSWORD},
    )


@pytest.fixture
async def challenged(make_client, secured) -> httpx.AsyncClient:
    """A client that passed the password step and was emailed a code."""
    pending = make_client()
    response = await password_login(pending, secured)
    assert response.status_code == 202, response.text
    return pending


@pytest.fixture
async def secured_client(challenged, mail, redis) -> httpx.AsyncClient:
    """A fully logged-in client for a 2FA user, ready to request new codes."""
    response = await challenged.post("/auth/2fa/verify", json={"code": mail.last_code})
    assert response.status_code == 200, response.text
    challenged.headers["X-CSRF-Token"] = challenged.cookies["csrf_token"]
    await clear_cooldowns(redis)
    return challenged


async def clear_cooldowns(redis) -> None:
    """Skip the one-email-per-minute limit between steps of a test."""
    async for key in redis.scan_iter("2fa:cooldown:*"):
        await redis.delete(key)


class TestHelpers:
    def test_codes_are_six_random_digits(self):
        codes = {generate_code() for _ in range(200)}

        assert all(len(code) == 6 and code.isdigit() for code in codes)
        assert len(codes) > 190

    @pytest.mark.parametrize(
        ("email", "hint"),
        [
            ("alice@example.com", "a***@example.com"),
            ("a@b.io", "a***@b.io"),
        ],
    )
    def test_mask_email(self, email, hint):
        assert mask_email(email) == hint


class TestEmailSender:
    async def test_unconfigured_mail_is_unavailable(self):
        sender = EmailSender(None)

        with pytest.raises(Exception) as error:
            await sender.send_code("a@example.com", "123456", "login")

        assert error.value.status_code == 503

    async def test_builds_a_plain_text_message(self):
        sent = []

        class Mailer:
            async def send_message(self, message):
                sent.append(message)

        await EmailSender(Mailer()).send_code("a@example.com", "123456", "login")

        [message] = sent
        assert message.subject == "Your Waurd login code"
        assert [r.email for r in message.recipients] == ["a@example.com"]
        assert "123456" in message.body
        assert "10 minutes" in message.body

    async def test_smtp_failure_is_bad_gateway(self):
        class Mailer:
            async def send_message(self, message):
                raise ConnectionErrors("smtp down")

        with pytest.raises(BadGatewayException):
            await EmailSender(Mailer()).send_code("a@example.com", "1", "login")

    def test_unconfigured_settings_give_no_mailer(self, monkeypatch):
        monkeypatch.setattr(settings, "MAIL_USERNAME", None)
        get_email_sender.cache_clear()
        try:
            assert get_email_sender().mailer is None
        finally:
            get_email_sender.cache_clear()

    def test_gmail_settings_build_a_mailer(self, monkeypatch):
        monkeypatch.setattr(settings, "MAIL_USERNAME", "sender@gmail.com")
        monkeypatch.setattr(settings, "MAIL_PASSWORD", "app-password")
        get_email_sender.cache_clear()
        try:
            config = get_email_sender().mailer.config
        finally:
            get_email_sender.cache_clear()

        assert config.MAIL_SERVER == "smtp.gmail.com"
        assert config.MAIL_PORT == 587
        assert config.MAIL_STARTTLS is True
        assert config.MAIL_FROM == "sender@gmail.com"


class TestStatus:
    async def test_disabled_by_default(self, alice_client):
        response = await alice_client.get("/auth/2fa")

        assert response.status_code == 200
        assert response.json() == {"enabled": False}

    async def test_reports_enabled(self, secured_client):
        assert (await secured_client.get("/auth/2fa")).json() == {"enabled": True}

    async def test_requires_authentication(self, client):
        assert (await client.get("/auth/2fa")).status_code == 401


class TestEnable:
    async def request_code(self, client, action="enable") -> httpx.Response:
        return await client.post("/auth/2fa/code", json={"action": action})

    async def test_code_is_emailed_to_the_account(self, alice_client, alice, mail):
        response = await self.request_code(alice_client)

        assert response.status_code == 202
        assert response.json() == {
            "detail": "Verification code sent",
            "email_hint": "a***@example.com",
        }
        [email] = mail.sent
        assert email.recipient == alice.email
        assert email.purpose == "enable"

    async def test_requesting_does_not_enable(self, alice_client, alice, session_maker):
        await self.request_code(alice_client)

        assert (await stored_user(session_maker, alice)).two_factor_enabled is False

    async def test_valid_code_enables(self, alice_client, alice, mail, session_maker):
        await self.request_code(alice_client)

        response = await alice_client.post(
            "/auth/2fa/enable", json={"code": mail.last_code}
        )

        assert response.status_code == 200
        assert response.json() == {"enabled": True}
        assert (await stored_user(session_maker, alice)).two_factor_enabled is True

    async def test_keeps_the_current_session(self, alice_client, mail):
        await self.request_code(alice_client)
        await alice_client.post("/auth/2fa/enable", json={"code": mail.last_code})

        assert (await alice_client.get("/users/me")).status_code == 200

    async def test_accepts_spaced_code(self, alice_client, mail):
        await self.request_code(alice_client)
        code = mail.last_code

        response = await alice_client.post(
            "/auth/2fa/enable", json={"code": f" {code[:3]} {code[3:]} "}
        )

        assert response.status_code == 200

    async def test_wrong_code_is_rejected(
        self, alice_client, alice, mail, session_maker
    ):
        await self.request_code(alice_client)

        response = await alice_client.post(
            "/auth/2fa/enable", json={"code": wrong(mail.last_code)}
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid verification code"}
        assert (await stored_user(session_maker, alice)).two_factor_enabled is False

    async def test_code_works_only_once(self, alice_client, mail, redis):
        await self.request_code(alice_client)
        code = mail.last_code
        await alice_client.post("/auth/2fa/enable", json={"code": code})

        # Turning it off must not accept the code that turned it on.
        await clear_cooldowns(redis)
        response = await alice_client.post("/auth/2fa/disable", json={"code": code})

        assert response.status_code == 400

    async def test_without_a_code_request(self, alice_client):
        response = await alice_client.post("/auth/2fa/enable", json={"code": "123456"})

        assert response.status_code == 400
        assert response.json() == {
            "detail": "No verification code requested or it expired. "
            "Request a new code."
        }

    async def test_expired_code(self, alice_client, mail, redis):
        await self.request_code(alice_client)
        async for key in redis.scan_iter("2fa:action:*"):
            assert 0 < await redis.ttl(key) <= 600
            await redis.delete(key)

        response = await alice_client.post(
            "/auth/2fa/enable", json={"code": mail.last_code}
        )

        assert response.status_code == 400

    async def test_locks_after_five_wrong_codes(self, alice_client, mail):
        await self.request_code(alice_client)
        code = mail.last_code
        for _ in range(5):
            await alice_client.post("/auth/2fa/enable", json={"code": wrong(code)})

        response = await alice_client.post("/auth/2fa/enable", json={"code": code})

        assert response.status_code == 429
        assert response.json() == {
            "detail": "Too many invalid codes. Request a new code."
        }

    async def test_new_code_replaces_the_old_one(self, alice_client, mail, redis):
        await self.request_code(alice_client)
        first = mail.last_code
        await clear_cooldowns(redis)
        await self.request_code(alice_client)

        if first != mail.last_code:
            response = await alice_client.post("/auth/2fa/enable", json={"code": first})
            assert response.status_code == 400

    async def test_cooldown_between_emails(self, alice_client, mail, redis):
        await self.request_code(alice_client)

        response = await self.request_code(alice_client)

        assert response.status_code == 429
        assert response.json() == {
            "detail": "A code was sent recently. Wait a minute before asking again."
        }
        assert len(mail.sent) == 1
        [key] = [key async for key in redis.scan_iter("2fa:cooldown:*")]
        assert 0 < await redis.ttl(key) <= 60

    async def test_failed_send_can_be_retried(self, alice_client, mail, redis):
        mail.fail = True
        failed = await self.request_code(alice_client)
        mail.fail = False

        retried = await self.request_code(alice_client)

        assert failed.status_code == 502
        assert [key async for key in redis.scan_iter("2fa:action:*")] != []
        assert retried.status_code == 202

    async def test_failed_send_leaves_no_usable_code(self, alice_client, mail, redis):
        mail.fail = True

        await self.request_code(alice_client)

        assert [key async for key in redis.scan_iter("2fa:*")] == []

    async def test_enable_when_already_enabled(self, secured_client):
        response = await self.request_code(secured_client)

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Two-factor authentication is already enabled"
        }

    @pytest.mark.parametrize(
        ("payload", "detail"),
        [
            ({}, "Code is required."),
            ({"code": "12345"}, "Code is invalid."),
            ({"code": "1234567"}, "Code is invalid."),
            ({"code": "12a456"}, "Code is invalid."),
            ({"code": 123456}, "Code is invalid."),
        ],
    )
    async def test_malformed_code(self, alice_client, payload, detail):
        response = await alice_client.post("/auth/2fa/enable", json=payload)

        assert response.status_code == 422
        assert response.json() == {"detail": detail}

    @pytest.mark.parametrize(
        ("payload", "detail"),
        [({}, "Value is required."), ({"action": "toggle"}, "Value is invalid.")],
    )
    async def test_malformed_action(self, alice_client, payload, detail):
        response = await alice_client.post("/auth/2fa/code", json=payload)

        assert response.status_code == 422
        assert response.json() == {"detail": detail}

    @pytest.mark.parametrize(
        ("path", "body"),
        [
            ("/auth/2fa/code", {"action": "enable"}),
            ("/auth/2fa/enable", {"code": "123456"}),
            ("/auth/2fa/disable", {"code": "123456"}),
        ],
    )
    async def test_requires_csrf_token(self, alice_client, path, body):
        del alice_client.headers["X-CSRF-Token"]

        assert (await alice_client.post(path, json=body)).status_code == 403

    @pytest.mark.parametrize(
        "path", ["/auth/2fa/code", "/auth/2fa/enable", "/auth/2fa/disable"]
    )
    async def test_requires_authentication(self, anon_with_csrf, path):
        response = await anon_with_csrf.post(
            path, json={"action": "enable", "code": "123456"}
        )

        assert response.status_code == 401


class TestLoginChallenge:
    async def test_password_login_emails_a_code(self, client, secured, mail):
        response = await password_login(client, secured)

        assert response.status_code == 202
        assert response.json() == {
            "detail": "Two-factor authentication required",
            "two_factor_required": True,
            "email_hint": "s***@example.com",
        }
        [email] = mail.sent
        assert email.recipient == secured.email
        assert email.purpose == "login"

    async def test_challenge_grants_no_session(self, challenged):
        assert "session_id" not in challenged.cookies
        assert "csrf_token" not in challenged.cookies
        assert (await challenged.get("/users/me")).status_code == 401

    async def test_challenge_cookie_is_http_only(self, client, secured):
        response = await password_login(client, secured)

        cookie = response.headers["set-cookie"].lower()
        assert cookie.startswith("two_factor_token=")
        assert "httponly" in cookie
        assert "max-age=600" in cookie

    async def test_wrong_password_sends_nothing(self, client, secured, mail):
        response = await client.post(
            "/auth/login",
            json={"email": secured.email, "password": "WrongPassword1!"},
        )

        assert response.status_code == 401
        assert mail.sent == []

    async def test_repeated_login_is_rate_limited(self, client, secured, mail):
        await password_login(client, secured)

        response = await password_login(client, secured)

        assert response.status_code == 429
        assert len(mail.sent) == 1

    async def test_email_failure_is_reported(self, client, secured, mail, redis):
        mail.fail = True

        response = await password_login(client, secured)

        assert response.status_code == 502
        assert "two_factor_token" not in client.cookies
        assert [key async for key in redis.scan_iter("2fa:*")] == []

    async def test_users_without_2fa_log_in_directly(self, client, alice, mail):
        response = await password_login(client, alice)

        assert response.status_code == 200
        assert "session_id" in client.cookies
        assert mail.sent == []


class TestVerify:
    async def test_valid_code_starts_a_session(self, challenged, secured, mail):
        response = await challenged.post(
            "/auth/2fa/verify", json={"code": mail.last_code}
        )

        assert response.status_code == 200
        assert response.json()["email"] == secured.email
        assert "two_factor_token" not in challenged.cookies
        assert challenged.cookies["csrf_token"]
        assert (await challenged.get("/users/me")).status_code == 200

    async def test_does_not_require_csrf(self, challenged, mail):
        # The browser has no CSRF cookie until this request succeeds.
        assert "X-CSRF-Token" not in challenged.headers

        response = await challenged.post(
            "/auth/2fa/verify", json={"code": mail.last_code}
        )

        assert response.status_code == 200

    async def test_code_works_only_once(self, challenged, mail):
        token = challenged.cookies["two_factor_token"]
        code = mail.last_code
        await challenged.post("/auth/2fa/verify", json={"code": code})

        challenged.cookies.set("two_factor_token", token)
        response = await challenged.post("/auth/2fa/verify", json={"code": code})

        assert response.status_code == 401
        assert response.json() == {"detail": "Verification code expired. Log in again."}

    async def test_code_is_bound_to_its_browser(self, make_client, challenged, mail):
        other = make_client()

        response = await other.post("/auth/2fa/verify", json={"code": mail.last_code})

        assert response.status_code == 401
        assert "session_id" not in other.cookies

    async def test_wrong_code_keeps_the_challenge(self, challenged, mail):
        bad = await challenged.post(
            "/auth/2fa/verify", json={"code": wrong(mail.last_code)}
        )
        good = await challenged.post("/auth/2fa/verify", json={"code": mail.last_code})

        assert bad.status_code == 401
        assert bad.json() == {"detail": "Invalid verification code"}
        assert good.status_code == 200

    async def test_locks_after_five_wrong_codes(self, challenged, mail):
        for _ in range(5):
            await challenged.post(
                "/auth/2fa/verify", json={"code": wrong(mail.last_code)}
            )

        response = await challenged.post(
            "/auth/2fa/verify", json={"code": mail.last_code}
        )

        assert response.status_code == 429
        assert response.json() == {
            "detail": "Too many invalid codes. Log in again to get a new code."
        }
        assert "session_id" not in challenged.cookies

    async def test_locked_challenge_is_gone(self, challenged, mail):
        for _ in range(6):
            await challenged.post(
                "/auth/2fa/verify", json={"code": wrong(mail.last_code)}
            )

        response = await challenged.post(
            "/auth/2fa/verify", json={"code": mail.last_code}
        )

        assert response.status_code == 401

    async def test_logging_in_again_sends_a_new_code(
        self, make_client, challenged, secured, mail, redis
    ):
        await clear_cooldowns(redis)
        fresh = make_client()

        await password_login(fresh, secured)
        response = await fresh.post("/auth/2fa/verify", json={"code": mail.last_code})

        assert len(mail.sent) == 2
        assert response.status_code == 200

    async def test_without_challenge_cookie(self, client):
        response = await client.post("/auth/2fa/verify", json={"code": "123456"})

        assert response.status_code == 401

    async def test_forged_challenge_cookie(self, client):
        client.cookies.set("two_factor_token", "forged")

        response = await client.post("/auth/2fa/verify", json={"code": "123456"})

        assert response.status_code == 401

    async def test_expired_challenge(self, challenged, mail, redis):
        token = challenged.cookies["two_factor_token"]
        assert 0 < await redis.ttl(f"2fa:login:{token}") <= 600
        await redis.delete(f"2fa:login:{token}")

        response = await challenged.post(
            "/auth/2fa/verify", json={"code": mail.last_code}
        )

        assert response.status_code == 401


class TestDisable:
    async def test_valid_code_disables(
        self, secured_client, secured, mail, session_maker
    ):
        sent = await secured_client.post("/auth/2fa/code", json={"action": "disable"})

        response = await secured_client.post(
            "/auth/2fa/disable", json={"code": mail.last_code}
        )

        assert sent.status_code == 202
        assert mail.sent[-1].purpose == "disable"
        assert response.status_code == 200
        assert response.json() == {"enabled": False}
        assert (await stored_user(session_maker, secured)).two_factor_enabled is False

    async def test_login_no_longer_asks_for_a_code(
        self, secured_client, secured, mail, client
    ):
        await secured_client.post("/auth/2fa/code", json={"action": "disable"})
        await secured_client.post("/auth/2fa/disable", json={"code": mail.last_code})

        response = await password_login(client, secured)

        assert response.status_code == 200

    async def test_enable_code_cannot_disable(
        self, secured_client, secured, session_maker, redis
    ):
        # An enable code can't be requested once 2FA is on, so plant one to
        # check that codes are bound to their action.
        store = TwoFactorStore(
            redis, code_ttl_seconds=600, max_attempts=5, resend_cooldown_seconds=60
        )
        await store.create_action_code(secured.id, TwoFactorAction.ENABLE, "424242")

        response = await secured_client.post(
            "/auth/2fa/disable", json={"code": "424242"}
        )

        assert response.status_code == 400
        assert (await stored_user(session_maker, secured)).two_factor_enabled is True

    async def test_login_code_cannot_disable(self, challenged, mail, secured):
        login_code = mail.last_code
        await challenged.post("/auth/2fa/verify", json={"code": login_code})
        challenged.headers["X-CSRF-Token"] = challenged.cookies["csrf_token"]

        response = await challenged.post("/auth/2fa/disable", json={"code": login_code})

        assert response.status_code == 400

    async def test_wrong_code_is_rejected(
        self, secured_client, secured, mail, session_maker
    ):
        await secured_client.post("/auth/2fa/code", json={"action": "disable"})

        response = await secured_client.post(
            "/auth/2fa/disable", json={"code": wrong(mail.last_code)}
        )

        assert response.status_code == 400
        assert (await stored_user(session_maker, secured)).two_factor_enabled is True

    async def test_not_enabled(self, alice_client):
        code = await alice_client.post("/auth/2fa/code", json={"action": "disable"})
        disable = await alice_client.post("/auth/2fa/disable", json={"code": "123456"})

        assert code.status_code == 400
        assert disable.status_code == 400
        assert disable.json() == {"detail": "Two-factor authentication is not enabled"}


class TestGoogleLogin:
    FRONTEND = "http://frontend.example/app?tab=play"

    @pytest.fixture(autouse=True)
    def mock_google(self, monkeypatch):
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "client-secret")
        monkeypatch.setattr(settings, "GOOGLE_FRONTEND_REDIRECT_URI", self.FRONTEND)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/token":
                return httpx.Response(200, json={"access_token": "token"})
            return httpx.Response(200, json=GOOGLE_PROFILE)

        def client_factory(**kwargs) -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

        monkeypatch.setattr(
            auth_endpoints,
            "httpx",
            SimpleNamespace(AsyncClient=client_factory, HTTPError=httpx.HTTPError),
        )

    async def google_login(self, client: httpx.AsyncClient) -> httpx.Response:
        start = await client.get("/auth/google")
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        return await client.get(
            "/auth/google/callback",
            params={"code": "auth-code", "state": state},
        )

    async def test_2fa_user_is_challenged(self, client, make_user, mail):
        await make_user(
            email=GOOGLE_PROFILE["email"],
            password_hash=None,
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id=GOOGLE_PROFILE["sub"],
            two_factor_enabled=True,
        )

        response = await self.google_login(client)

        assert response.status_code == 303
        location = urlparse(response.headers["location"])
        assert parse_qs(location.query) == {"tab": ["play"], "two_factor": ["required"]}
        assert "session_id" not in client.cookies
        assert mail.sent[-1].recipient == GOOGLE_PROFILE["email"]

        verified = await client.post("/auth/2fa/verify", json={"code": mail.last_code})
        assert verified.status_code == 200
        assert verified.json()["email"] == GOOGLE_PROFILE["email"]

    async def test_user_without_2fa_gets_a_session(self, client, mail):
        response = await self.google_login(client)

        assert response.status_code == 303
        assert response.headers["location"] == self.FRONTEND
        assert "session_id" in client.cookies
        assert mail.sent == []


def test_action_enum_values():
    assert {action.value for action in TwoFactorAction} == {"enable", "disable"}
