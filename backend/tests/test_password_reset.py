"""Tests for password reset with emailed one-time links.

Uses the fixtures in tests/conftest.py from the backend API test suite. Email is
replaced by a fake sender that records links instead of sending them.
"""

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

import pytest

# This suite lives on backend/api-tests, which may not contain the reset code
# yet. Skip instead of failing collection until it is merged in.
pytest.importorskip("fastapi_mail", reason="Email dependencies are not installed")
pytest.importorskip(
    "backend.api.v1.endpoints.password",
    reason="Password reset is not merged into this branch",
)

from conftest import PASSWORD

from backend.core.config import settings
from backend.core.email import EmailSender, get_email_sender
from backend.core.exceptions import BadGatewayException
from backend.core.password_reset import PasswordResetStore, build_reset_link
from backend.main import app
from backend.models import OAuthProvider, User

NEW_PASSWORD = "BrandNewPassw0rd!"
SENT = "If an account with that email exists, a reset link is on its way."
INVALID = "This reset link is invalid or has expired. Request a new one."


@dataclass
class SentLink:
    recipient: str
    link: str

    @property
    def token(self) -> str:
        return parse_qs(urlparse(self.link).query)["token"][0]


@dataclass
class FakeSender:
    sent: list[SentLink] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    fail: bool = False
    is_configured: bool = True

    async def send_password_reset_link(self, recipient, link):
        if self.fail:
            raise BadGatewayException("Could not send the verification email")
        self.sent.append(SentLink(recipient, link))

    async def send_code(self, recipient, code, purpose):
        self.codes.append(code)

    @property
    def last_token(self) -> str:
        return self.sent[-1].token


@pytest.fixture(autouse=True)
def mail() -> FakeSender:
    sender = FakeSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    return sender


async def forgot(client, email: str):
    return await client.post("/auth/password/forgot", json={"email": email})


async def reset(client, token: str, new_password: str = NEW_PASSWORD):
    return await client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": new_password},
    )


async def login(client, email: str, password: str):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def reset_keys(redis) -> list[str]:
    return [key async for key in redis.scan_iter("password-reset:*")]


class TestLinkHelpers:
    @pytest.mark.parametrize(
        ("base", "expected"),
        [
            (
                "http://localhost:5173/reset-password",
                "http://localhost:5173/reset-password?token=abc",
            ),
            (
                "https://waurd.example/auth/reset?lang=en",
                "https://waurd.example/auth/reset?lang=en&token=abc",
            ),
        ],
    )
    def test_build_reset_link(self, base, expected):
        assert build_reset_link(base, "abc") == expected

    async def test_message_content(self):
        sent = []

        class Mailer:
            async def send_message(self, message):
                sent.append(message)

        await EmailSender(Mailer()).send_password_reset_link(
            "a@example.com", "http://localhost:5173/reset-password?token=abc"
        )

        [message] = sent
        assert message.subject == "Reset your Waurd password"
        assert "http://localhost:5173/reset-password?token=abc" in message.body
        assert "expires in 30 minutes" in message.body
        assert "ignore this email" in message.body

    async def test_unconfigured_sender_is_unavailable(self):
        with pytest.raises(Exception) as error:
            await EmailSender(None).send_password_reset_link("a@example.com", "x")

        assert error.value.status_code == 503


class TestForgotPassword:
    async def test_emails_a_link_to_the_frontend(self, client, alice, mail):
        response = await forgot(client, alice.email)

        assert response.status_code == 202
        assert response.json() == {"detail": SENT}
        [sent] = mail.sent
        assert sent.recipient == alice.email
        link = urlparse(sent.link)
        assert (
            f"{link.scheme}://{link.netloc}{link.path}" == settings.PASSWORD_RESET_URL
        )
        assert len(sent.token) >= 40

    async def test_sends_no_code(self, client, alice, mail):
        await forgot(client, alice.email)

        assert mail.codes == []

    async def test_unknown_email_gets_the_same_answer(self, client, alice, mail):
        known = await forgot(client, alice.email)
        unknown = await forgot(client, "nobody@example.com")

        assert unknown.status_code == known.status_code == 202
        assert unknown.json() == known.json()
        assert [sent.recipient for sent in mail.sent] == [alice.email]

    async def test_google_only_account_gets_no_link(self, client, make_user, mail):
        user = await make_user(
            password_hash=None,
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id="google-1",
        )

        response = await forgot(client, user.email)

        assert response.status_code == 202
        assert mail.sent == []

    async def test_email_whitespace_is_ignored(self, client, alice, mail):
        await forgot(client, f"  {alice.email}  ")

        assert len(mail.sent) == 1

    async def test_repeat_within_a_minute_sends_nothing_more(
        self, client, alice, mail, redis
    ):
        await forgot(client, alice.email)

        second = await forgot(client, alice.email)

        assert second.status_code == 202
        assert second.json() == {"detail": SENT}
        assert len(mail.sent) == 1
        [key] = [k for k in await reset_keys(redis) if ":cooldown:" in k]
        assert 0 < await redis.ttl(key) <= 60

    async def test_does_not_block_a_2fa_login_code(self, client, make_user, mail):
        user = await make_user(two_factor_enabled=True)
        await forgot(client, user.email)

        response = await login(client, user.email, PASSWORD)

        assert response.status_code == 202
        assert len(mail.codes) == 1

    async def test_link_expires(self, client, alice, mail, redis):
        await forgot(client, alice.email)

        [key] = [k for k in await reset_keys(redis) if ":token:" in k]
        assert 0 < await redis.ttl(key) <= 1800

    async def test_token_is_not_stored_in_plain_text(self, client, alice, mail, redis):
        await forgot(client, alice.email)

        for key in await reset_keys(redis):
            assert mail.last_token not in key
            assert mail.last_token != await redis.get(key)

    async def test_failed_send_can_be_retried(self, client, alice, mail, redis):
        mail.fail = True
        failed = await forgot(client, alice.email)
        mail.fail = False

        assert failed.status_code == 202
        assert await reset_keys(redis) == []

        await forgot(client, alice.email)
        assert len(mail.sent) == 1

    async def test_unconfigured_email_is_unavailable(self, client, alice, mail):
        mail.is_configured = False

        response = await forgot(client, alice.email)

        assert response.status_code == 503
        assert response.json() == {"detail": "Email delivery is not configured"}

    async def test_invalid_email_is_rejected(self, client):
        response = await forgot(client, "not-an-email")

        assert response.status_code == 422
        assert response.json() == {"detail": "Email must be a valid email address."}

    async def test_does_not_change_the_password(self, client, alice):
        await forgot(client, alice.email)

        assert (await login(client, alice.email, PASSWORD)).status_code == 200


class TestResetPassword:
    async def test_link_sets_the_new_password(self, client, alice, mail):
        await forgot(client, alice.email)

        response = await reset(client, mail.last_token)

        assert response.status_code == 200
        assert response.json() == {
            "detail": "Password updated. Log in with your new password."
        }
        assert (await login(client, alice.email, NEW_PASSWORD)).status_code == 200

    async def test_old_password_stops_working(self, client, alice, mail):
        await forgot(client, alice.email)
        await reset(client, mail.last_token)

        assert (await login(client, alice.email, PASSWORD)).status_code == 401

    async def test_signs_out_existing_sessions(self, alice_client, client, alice, mail):
        await forgot(client, alice.email)
        await reset(client, mail.last_token)

        assert (await alice_client.get("/users/me")).status_code == 401

    async def test_keeps_other_users_signed_in(self, bob_client, client, alice, mail):
        await forgot(client, alice.email)
        await reset(client, mail.last_token)

        assert (await bob_client.get("/users/me")).status_code == 200

    async def test_link_works_only_once(self, client, alice, mail, redis):
        await forgot(client, alice.email)
        token = mail.last_token
        await reset(client, token)

        response = await reset(client, token, "AnotherPassw0rd!")

        assert response.status_code == 400
        assert response.json() == {"detail": INVALID}
        assert (await login(client, alice.email, NEW_PASSWORD)).status_code == 200
        assert [k for k in await reset_keys(redis) if ":cooldown:" not in k] == []

    async def test_new_request_invalidates_the_old_link(
        self, client, alice, mail, redis
    ):
        await forgot(client, alice.email)
        first = mail.last_token
        for key in await reset_keys(redis):
            if ":cooldown:" in key:
                await redis.delete(key)
        await forgot(client, alice.email)

        old = await reset(client, first)
        new = await reset(client, mail.last_token)

        assert first != mail.last_token
        assert old.status_code == 400
        assert new.status_code == 200

    async def test_link_resets_only_its_own_account(self, client, alice, bob, mail):
        await forgot(client, bob.email)
        await reset(client, mail.last_token)

        assert (await login(client, alice.email, PASSWORD)).status_code == 200
        assert (await login(client, bob.email, NEW_PASSWORD)).status_code == 200

    async def test_made_up_token(self, client):
        response = await reset(client, "not-a-real-token")

        assert response.status_code == 400
        assert response.json() == {"detail": INVALID}

    async def test_expired_link(self, client, alice, mail, redis):
        await forgot(client, alice.email)
        for key in await reset_keys(redis):
            await redis.delete(key)

        response = await reset(client, mail.last_token)

        assert response.status_code == 400
        assert (await login(client, alice.email, PASSWORD)).status_code == 200

    async def test_account_deleted_after_request(
        self, client, alice, mail, session_maker
    ):
        await forgot(client, alice.email)
        async with session_maker() as session:
            await session.delete(await session.get(User, alice.id))
            await session.commit()

        response = await reset(client, mail.last_token)

        assert response.status_code == 400

    async def test_store_hands_out_distinct_tokens(self, redis):
        store = PasswordResetStore(redis, ttl_seconds=60, cooldown_seconds=60)

        first = await store.create_token("00000000-0000-4000-8000-000000000001")
        second = await store.create_token("00000000-0000-4000-8000-000000000002")

        assert first != second
        assert await store.consume_token(first) == (
            "00000000-0000-4000-8000-000000000001"
        )
        assert await store.consume_token(first) is None

    async def test_2fa_still_applies_after_reset(self, client, make_user, mail):
        user = await make_user(two_factor_enabled=True)
        await forgot(client, user.email)
        await reset(client, mail.last_token)

        response = await login(client, user.email, NEW_PASSWORD)

        assert response.status_code == 202

    async def test_needs_no_session_or_csrf(self, make_client, alice, mail):
        anonymous = make_client()
        await forgot(anonymous, alice.email)

        response = await reset(anonymous, mail.last_token)

        assert "X-CSRF-Token" not in anonymous.headers
        assert response.status_code == 200

    async def test_stores_a_hash_not_the_password(
        self, client, alice, mail, session_maker
    ):
        await forgot(client, alice.email)
        await reset(client, mail.last_token)

        async with session_maker() as session:
            stored = await session.get(User, alice.id)
        assert stored.password_hash != NEW_PASSWORD
        assert stored.password_hash.startswith("$argon2")

    @pytest.mark.parametrize(
        ("payload", "detail"),
        [
            (
                {"token": "abc", "new_password": "short"},
                "Password must be at least 8 characters.",
            ),
            (
                {"token": "abc", "new_password": "p" * 129},
                "Password must be at most 128 characters.",
            ),
            ({"new_password": NEW_PASSWORD}, "Reset token is required."),
            ({"token": "abc"}, "Password is required."),
            (
                {"token": "", "new_password": NEW_PASSWORD},
                "Reset token must be at least 1 characters.",
            ),
        ],
    )
    async def test_invalid_payload(self, client, payload, detail):
        response = await client.post("/auth/password/reset", json=payload)

        assert response.status_code == 422
        assert response.json() == {"detail": detail}

    async def test_invalid_password_does_not_spend_the_link(self, client, alice, mail):
        await forgot(client, alice.email)

        await reset(client, mail.last_token, "short")
        response = await reset(client, mail.last_token)

        assert response.status_code == 200
