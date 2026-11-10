"""Tests for the /users endpoints."""

import uuid

from conftest import PASSWORD
from sqlalchemy import delete

from backend.core.config import settings
from backend.models import Match, MatchStatus, User, UserStats


def user_uuid(user: User) -> str:
    return str(uuid.UUID(bytes=user.id))


def update_payload(**overrides):
    return {
        "username": "renamed",
        "email": "renamed@example.com",
        "password": "BrandNewPassw0rd!",
        **overrides,
    }


class TestSessionAuthentication:
    """Authentication behaviour shared by every protected endpoint."""

    async def test_no_cookie_is_unauthorized(self, client):
        response = await client.get("/users/me")

        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required"}

    async def test_unknown_session_is_unauthorized(self, client):
        client.cookies.set("session_id", "made-up-session")

        response = await client.get("/users/me")

        assert response.status_code == 401
        assert response.json() == {"detail": "Session expired or invalid"}

    async def test_session_of_deleted_user_is_unauthorized(
        self, alice_client, alice, session_maker
    ):
        async with session_maker() as session:
            await session.execute(delete(User).where(User.id == alice.id))
            await session.commit()

        response = await alice_client.get("/users/me")

        assert response.status_code == 401
        assert response.json() == {"detail": "User not found"}

    async def test_activity_renews_session_ttl(self, alice_client, redis):
        session_key = f"session:{alice_client.cookies['session_id']}"
        await redis.expire(session_key, 10)

        await alice_client.get("/users/me")

        assert await redis.ttl(session_key) > 10

    async def test_get_requests_do_not_need_csrf(self, alice_client):
        del alice_client.headers["X-CSRF-Token"]

        response = await alice_client.get("/users/me")

        assert response.status_code == 200


class TestGetMe:
    async def test_returns_the_current_user(self, alice_client, alice):
        response = await alice_client.get("/users/me")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == user_uuid(alice)
        assert body["username"] == "alice"
        assert body["email"] == "alice@example.com"

    async def test_does_not_expose_sensitive_columns(self, alice_client):
        response = await alice_client.get("/users/me")

        assert set(response.json()) == {
            "id",
            "username",
            "email",
            "avatar_url",
            "created_at",
            "updated_at",
        }


class TestUpdateMe:
    async def test_updates_profile(self, alice_client, alice, session_maker):
        response = await alice_client.patch(
            "/users/me",
            json=update_payload(avatar_url="https://example.com/a.png"),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == user_uuid(alice)
        assert body["username"] == "renamed"
        assert body["email"] == "renamed@example.com"
        assert body["avatar_url"] == "https://example.com/a.png"
        async with session_maker() as session:
            stored = await session.get(User, alice.id)
        assert stored.username == "renamed"

    async def test_new_password_replaces_old_one(self, alice_client, client):
        await alice_client.patch("/users/me", json=update_payload())

        old = await client.post(
            "/auth/login",
            json={"email": "renamed@example.com", "password": PASSWORD},
        )
        new = await client.post(
            "/auth/login",
            json={"email": "renamed@example.com", "password": "BrandNewPassw0rd!"},
        )

        assert old.status_code == 401
        assert new.status_code == 200

    async def test_revokes_all_of_the_users_sessions(self, login_as, alice):
        first = await login_as(alice)
        second = await login_as(alice)

        await first.patch("/users/me", json=update_payload())

        assert (await first.get("/users/me")).status_code == 401
        assert (await second.get("/users/me")).status_code == 401

    async def test_keeps_other_users_sessions(self, alice_client, bob_client):
        await alice_client.patch("/users/me", json=update_payload())

        assert (await bob_client.get("/users/me")).status_code == 200

    async def test_keeping_own_username_and_email_is_allowed(self, alice_client, alice):
        response = await alice_client.patch(
            "/users/me",
            json=update_payload(username=alice.username, email=alice.email),
        )

        assert response.status_code == 200

    async def test_taken_username_is_rejected(self, alice_client, bob):
        response = await alice_client.patch(
            "/users/me",
            json=update_payload(username=bob.username),
        )

        assert response.status_code == 409
        assert response.json() == {"detail": "Username already taken."}
        assert (await alice_client.get("/users/me")).json()["username"] == "alice"

    async def test_taken_email_is_rejected(self, alice_client, bob):
        response = await alice_client.patch(
            "/users/me",
            json=update_payload(email=bob.email),
        )

        assert response.status_code == 409
        assert response.json() == {"detail": "Email already registered."}

    async def test_rejected_update_keeps_the_session(self, alice_client, bob):
        await alice_client.patch("/users/me", json=update_payload(email=bob.email))

        assert (await alice_client.get("/users/me")).status_code == 200

    async def test_invalid_field_is_rejected(self, alice_client):
        response = await alice_client.patch(
            "/users/me",
            json=update_payload(username="ab"),
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "Username must be at least 3 characters."}

    async def test_requires_authentication(self, anon_with_csrf):
        response = await anon_with_csrf.patch("/users/me", json=update_payload())

        assert response.status_code == 401

    async def test_requires_csrf_token(self, alice_client):
        del alice_client.headers["X-CSRF-Token"]

        response = await alice_client.patch("/users/me", json=update_payload())

        assert response.status_code == 403
        assert (await alice_client.get("/users/me")).json()["username"] == "alice"

    async def test_partial_update_is_accepted(self, alice_client):
        response = await alice_client.patch(
            "/users/me",
            json={"avatar_url": "https://example.com/a.png"},
        )

        assert response.status_code == 200

    async def test_succeeds_while_an_oauth_login_is_in_progress(
        self, alice_client, client, monkeypatch
    ):
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
        await client.get("/auth/google")

        response = await alice_client.patch("/users/me", json=update_payload())

        assert response.status_code == 200


class TestGetUserById:
    async def test_returns_own_profile(self, alice_client, alice):
        response = await alice_client.get(f"/users/{user_uuid(alice)}")

        assert response.status_code == 200
        assert response.json()["id"] == user_uuid(alice)

    async def test_other_users_profile_is_forbidden(self, alice_client, bob):
        response = await alice_client.get(f"/users/{user_uuid(bob)}")

        assert response.status_code == 403
        assert response.json() == {
            "detail": "You do not have permission to access this user's information."
        }

    async def test_invalid_uuid_is_rejected(self, alice_client):
        response = await alice_client.get("/users/not-a-uuid")

        assert response.status_code == 422
        assert response.json() == {"detail": "User ID is invalid."}

    async def test_requires_authentication(self, client, alice):
        response = await client.get(f"/users/{user_uuid(alice)}")

        assert response.status_code == 401


class TestGetUserStats:
    async def test_returns_own_stats(self, alice_client, alice, session_maker):
        async with session_maker() as session:
            session.add(
                UserStats(
                    user_id=alice.id,
                    matches_played=10,
                    wins=6,
                    losses=3,
                    draws=1,
                    rating_elo=1350,
                    highest_scoring_word="QUIZZIFY",
                    highest_word_score=100,
                    total_damage_dealt=5000,
                )
            )
            await session.commit()

        response = await alice_client.get(f"/users/{user_uuid(alice)}/stats")

        assert response.status_code == 200
        assert response.json() == {
            "user_id": user_uuid(alice),
            "matches_played": 10,
            "wins": 6,
            "losses": 3,
            "draws": 1,
            "rating_elo": 1350,
            "highest_scoring_word": "QUIZZIFY",
            "highest_word_score": 100,
            "total_damage_dealt": 5000,
        }

    async def test_user_without_stats_is_not_found(self, alice_client, alice):
        response = await alice_client.get(f"/users/{user_uuid(alice)}/stats")

        assert response.status_code == 404
        assert response.json() == {"detail": "User statistics not found"}

    async def test_other_users_stats_are_forbidden(self, alice_client, bob):
        response = await alice_client.get(f"/users/{user_uuid(bob)}/stats")

        assert response.status_code == 403

    async def test_invalid_uuid_is_rejected(self, alice_client):
        response = await alice_client.get("/users/not-a-uuid/stats")

        assert response.status_code == 422

    async def test_requires_authentication(self, client, alice):
        response = await client.get(f"/users/{user_uuid(alice)}/stats")

        assert response.status_code == 401


class TestGetUserMatches:
    # 0xff can never appear in UTF-8, so these are deterministic stand-ins for the
    # non-text bytes that almost every real uuid4 contains.
    MATCH_ID = uuid.UUID("ffffffff-0000-4000-8000-000000000001")

    async def add_match(self, session_maker, player1, player2):
        async with session_maker() as session:
            session.add(
                Match(
                    id=self.MATCH_ID.bytes,
                    player1_id=player1.id,
                    player2_id=player2.id,
                    time_control_seconds=300,
                    status=MatchStatus.FINISHED,
                )
            )
            await session.commit()

    async def test_user_without_matches_gets_empty_list(self, alice_client, alice):
        response = await alice_client.get(f"/users/{user_uuid(alice)}/matches")

        assert response.status_code == 200
        assert response.json() == []

    async def test_other_users_matches_are_forbidden(self, alice_client, bob):
        response = await alice_client.get(f"/users/{user_uuid(bob)}/matches")

        assert response.status_code == 403

    async def test_excludes_matches_of_other_players(
        self, alice_client, alice, bob, carol, session_maker
    ):
        await self.add_match(session_maker, bob, carol)

        response = await alice_client.get(f"/users/{user_uuid(alice)}/matches")

        assert response.json() == []

    async def test_invalid_uuid_is_rejected(self, alice_client):
        response = await alice_client.get("/users/not-a-uuid/matches")

        assert response.status_code == 422

    async def test_requires_authentication(self, client, alice):
        response = await client.get(f"/users/{user_uuid(alice)}/matches")

        assert response.status_code == 401

    async def test_returns_matches_with_uuid_ids(
        self, alice_client, alice, bob, session_maker
    ):
        await self.add_match(session_maker, alice, bob)

        response = await alice_client.get(f"/users/{user_uuid(alice)}/matches")

        assert response.status_code == 200
        match = response.json()[0]
        assert match["id"] == str(self.MATCH_ID)
        assert match["player1_id"] == user_uuid(alice)
        assert match["player2_id"] == user_uuid(bob)
        assert match["status"] == "FINISHED"
