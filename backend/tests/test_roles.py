"""Tests for roles (USER and GAME_MASTER) and game master user management.

Uses the fixtures in tests/conftest.py from the backend API test suite.
"""

import uuid

import pytest

# This suite lives on backend/api-tests, which may not contain roles yet.
# Skip instead of failing collection until they are merged in.
pytest.importorskip(
    "backend.api.v1.endpoints.admin", reason="Roles are not merged into this branch"
)

from sqlalchemy import func, select

from backend.models import Friendship, FriendshipStatus, User, UserRole, UserStats

GM_ONLY = "Game master role required"


def uid(user: User) -> str:
    return str(uuid.UUID(bytes=user.id))


@pytest.fixture
async def gm(make_user) -> User:
    return await make_user(
        username="gamemaster", email="gm@example.com", role=UserRole.GAME_MASTER
    )


@pytest.fixture
async def gm_client(login_as, gm):
    return await login_as(gm)


async def count(session_maker, model) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).select_from(model))


class TestDefaultRole:
    async def test_new_users_are_normal_users(self, client):
        response = await client.post(
            "/auth/register",
            json={
                "username": "newbie",
                "email": "newbie@example.com",
                "password": "SecureP@ssw0rd!123",
            },
        )

        assert response.json()["role"] == "USER"

    async def test_me_reports_the_role(self, alice_client, gm_client):
        assert (await alice_client.get("/users/me")).json()["role"] == "USER"
        assert (await gm_client.get("/users/me")).json()["role"] == "GAME_MASTER"

    async def test_users_cannot_promote_themselves(self, alice_client, alice):
        response = await alice_client.patch(
            "/users/me", json={"username": "alice2", "role": "GAME_MASTER"}
        )

        assert response.status_code == 200
        assert response.json()["role"] == "USER"


class TestAccess:
    ENDPOINTS = (
        ("get", "/admin/users", None),
        ("get", "/admin/users/{id}", None),
        ("patch", "/admin/users/{id}", {"username": "hacked"}),
        ("delete", "/admin/users/{id}", None),
    )

    @pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
    async def test_normal_users_are_refused(
        self, alice_client, bob, session_maker, method, path, body
    ):
        kwargs = {"json": body} if body else {}

        response = await getattr(alice_client, method)(
            path.format(id=uid(bob)), **kwargs
        )

        assert response.status_code == 403
        assert response.json() == {"detail": GM_ONLY}
        assert await count(session_maker, User) == 2

    @pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
    async def test_requires_authentication(
        self, anon_with_csrf, bob, method, path, body
    ):
        kwargs = {"json": body} if body else {}

        response = await getattr(anon_with_csrf, method)(
            path.format(id=uid(bob)), **kwargs
        )

        assert response.status_code == 401

    @pytest.mark.parametrize(
        ("method", "body"), [("patch", {"username": "x_changed"}), ("delete", None)]
    )
    async def test_mutations_require_csrf(self, gm_client, bob, method, body):
        del gm_client.headers["X-CSRF-Token"]
        kwargs = {"json": body} if body else {}

        response = await getattr(gm_client, method)(
            f"/admin/users/{uid(bob)}", **kwargs
        )

        assert response.status_code == 403

    async def test_promotion_takes_effect_immediately(
        self, gm_client, alice_client, alice
    ):
        await gm_client.patch(
            f"/admin/users/{uid(alice)}", json={"role": "GAME_MASTER"}
        )

        assert (await alice_client.get("/admin/users")).status_code == 200

    async def test_demotion_takes_effect_immediately(
        self, gm_client, login_as, make_user
    ):
        other = await make_user(role=UserRole.GAME_MASTER)
        other_client = await login_as(other)

        await gm_client.patch(f"/admin/users/{uid(other)}", json={"role": "USER"})

        assert (await other_client.get("/admin/users")).status_code == 403


class TestGameMasterViews:
    @pytest.mark.parametrize("suffix", ["", "/matches"])
    async def test_can_view_other_users(self, gm_client, alice, suffix):
        response = await gm_client.get(f"/users/{uid(alice)}{suffix}")

        assert response.status_code == 200

    async def test_can_view_other_users_stats(self, gm_client, alice, session_maker):
        async with session_maker() as session:
            session.add(UserStats(user_id=alice.id, wins=3))
            await session.commit()

        response = await gm_client.get(f"/users/{uid(alice)}/stats")

        assert response.status_code == 200
        assert response.json()["wins"] == 3

    @pytest.mark.parametrize("suffix", ["", "/stats", "/matches"])
    async def test_normal_users_still_cannot(self, alice_client, bob, suffix):
        response = await alice_client.get(f"/users/{uid(bob)}{suffix}")

        assert response.status_code == 403


class TestListUsers:
    async def test_lists_everyone(self, gm_client, gm, alice, bob):
        response = await gm_client.get("/admin/users")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert {user["username"] for user in body["users"]} == {
            "gamemaster",
            "alice",
            "bob",
        }

    async def test_shows_admin_fields_but_no_secrets(self, gm_client, alice):
        response = await gm_client.get("/admin/users")

        user = next(u for u in response.json()["users"] if u["username"] == "alice")
        assert user["role"] == "USER"
        assert user["oauth_provider"] == "LOCAL"
        assert user["two_factor_enabled"] is False
        assert user["is_online"] is False
        assert "password_hash" not in user
        assert "two_factor_secret" not in user

    @pytest.mark.parametrize(
        ("query", "expected"),
        [("ali", {"alice"}), ("BOB@EXAMPLE", {"bob"}), ("zzz", set())],
    )
    async def test_search(self, gm_client, alice, bob, query, expected):
        body = (await gm_client.get("/admin/users", params={"q": query})).json()

        assert {user["username"] for user in body["users"]} == expected
        assert body["total"] == len(expected)

    async def test_pagination(self, gm_client, gm, alice, bob, carol):
        first = (
            await gm_client.get("/admin/users", params={"limit": 2, "offset": 0})
        ).json()
        second = (
            await gm_client.get("/admin/users", params={"limit": 2, "offset": 2})
        ).json()

        assert first["total"] == second["total"] == 4
        assert len(first["users"]) == 2
        assert len(second["users"]) == 2
        names = [u["username"] for u in first["users"] + second["users"]]
        assert sorted(names) == ["alice", "bob", "carol", "gamemaster"]

    @pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
    async def test_invalid_paging(self, gm_client, params):
        response = await gm_client.get("/admin/users", params=params)

        assert response.status_code == 422


class TestGetUser:
    async def test_returns_details(self, gm_client, alice):
        response = await gm_client.get(f"/admin/users/{uid(alice)}")

        assert response.status_code == 200
        assert response.json()["email"] == alice.email

    async def test_unknown_user(self, gm_client):
        response = await gm_client.get(f"/admin/users/{uuid.uuid4()}")

        assert response.status_code == 404
        assert response.json() == {"detail": "User not found"}

    async def test_invalid_id(self, gm_client):
        response = await gm_client.get("/admin/users/not-a-uuid")

        assert response.status_code == 422


class TestUpdateUser:
    async def test_promote(self, gm_client, alice, session_maker):
        response = await gm_client.patch(
            f"/admin/users/{uid(alice)}", json={"role": "GAME_MASTER"}
        )

        assert response.status_code == 200
        assert response.json()["role"] == "GAME_MASTER"
        async with session_maker() as session:
            assert (await session.get(User, alice.id)).role == UserRole.GAME_MASTER

    async def test_edit_profile_fields(self, gm_client, alice):
        response = await gm_client.patch(
            f"/admin/users/{uid(alice)}",
            json={
                "username": "alice_renamed",
                "email": "alice.new@example.com",
                "avatar_url": "https://example.com/a.png",
            },
        )

        body = response.json()
        assert response.status_code == 200
        assert body["username"] == "alice_renamed"
        assert body["email"] == "alice.new@example.com"
        assert body["avatar_url"] == "https://example.com/a.png"
        assert body["role"] == "USER"

    async def test_omitted_fields_stay(self, gm_client, alice):
        response = await gm_client.patch(f"/admin/users/{uid(alice)}", json={})

        assert response.status_code == 200
        assert response.json()["username"] == "alice"

    async def test_taken_username(self, gm_client, alice, bob):
        response = await gm_client.patch(
            f"/admin/users/{uid(alice)}", json={"username": "bob"}
        )

        assert response.status_code == 409
        assert response.json() == {"detail": "Username already taken."}

    async def test_taken_email(self, gm_client, alice, bob):
        response = await gm_client.patch(
            f"/admin/users/{uid(alice)}", json={"email": bob.email}
        )

        assert response.status_code == 409
        assert response.json() == {"detail": "Email already registered."}

    async def test_keeping_the_same_values(self, gm_client, alice):
        response = await gm_client.patch(
            f"/admin/users/{uid(alice)}",
            json={"username": "alice", "email": alice.email},
        )

        assert response.status_code == 200

    async def test_cannot_change_own_role(self, gm_client, gm, session_maker):
        response = await gm_client.patch(
            f"/admin/users/{uid(gm)}", json={"role": "USER"}
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "You cannot change your own role"}
        async with session_maker() as session:
            assert (await session.get(User, gm.id)).role == UserRole.GAME_MASTER

    async def test_can_edit_own_profile(self, gm_client, gm):
        response = await gm_client.patch(
            f"/admin/users/{uid(gm)}", json={"username": "gm_renamed"}
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "body",
        [
            {"role": "ADMIN"},
            {"role": "guest"},
            {"username": "ab"},
            {"email": "not-an-email"},
        ],
    )
    async def test_invalid_values(self, gm_client, alice, body):
        response = await gm_client.patch(f"/admin/users/{uid(alice)}", json=body)

        assert response.status_code == 422

    async def test_unknown_user(self, gm_client):
        response = await gm_client.patch(
            f"/admin/users/{uuid.uuid4()}", json={"role": "USER"}
        )

        assert response.status_code == 404


class TestDeleteUser:
    async def test_deletes_the_user(self, gm_client, alice, session_maker):
        response = await gm_client.delete(f"/admin/users/{uid(alice)}")

        assert response.status_code == 204
        assert (await gm_client.get(f"/admin/users/{uid(alice)}")).status_code == 404
        async with session_maker() as session:
            assert await session.get(User, alice.id) is None

    async def test_signs_the_user_out(self, gm_client, alice_client, alice, redis):
        session_key = f"session:{alice_client.cookies['session_id']}"

        await gm_client.delete(f"/admin/users/{uid(alice)}")

        assert (await alice_client.get("/users/me")).status_code == 401
        # Removed outright, not just left pointing at a missing user.
        assert await redis.exists(session_key) == 0

    async def test_removes_what_belongs_to_the_user(
        self, gm_client, alice, bob, make_friendship, session_maker
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)
        async with session_maker() as session:
            session.add(UserStats(user_id=alice.id))
            await session.commit()

        await gm_client.delete(f"/admin/users/{uid(alice)}")

        assert await count(session_maker, Friendship) == 0
        assert await count(session_maker, UserStats) == 0
        async with session_maker() as session:
            assert await session.get(User, bob.id) is not None

    async def test_cannot_delete_self(self, gm_client, gm, session_maker):
        response = await gm_client.delete(f"/admin/users/{uid(gm)}")

        assert response.status_code == 400
        assert response.json() == {"detail": "You cannot delete your own account here"}
        async with session_maker() as session:
            assert await session.get(User, gm.id) is not None

    async def test_unknown_user(self, gm_client):
        response = await gm_client.delete(f"/admin/users/{uuid.uuid4()}")

        assert response.status_code == 404
