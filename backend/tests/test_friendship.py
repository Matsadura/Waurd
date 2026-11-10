"""Tests for the /friends endpoints."""

import uuid

import pytest
from sqlalchemy import func, select

from backend.models import Friendship, FriendshipStatus, User

UNKNOWN_USER_ID = "00000000-0000-4000-8000-00000000dead"


def user_uuid(user: User) -> str:
    return str(uuid.UUID(bytes=user.id))


def usernames(users: list[dict]) -> set[str]:
    return {user["username"] for user in users}


async def count_friendships(session_maker) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).select_from(Friendship))


async def get_friendship(session_maker, friendship_id) -> Friendship | None:
    async with session_maker() as session:
        return await session.get(Friendship, friendship_id)


class TestAccessControl:
    ENDPOINTS = (
        ("get", "/friends", None),
        ("get", "/friends/requests", None),
        ("post", "/friends/requests", {"username": "bob"}),
        ("patch", "/friends/requests/1", {"action": "ACCEPTED"}),
        ("delete", f"/friends/{UNKNOWN_USER_ID}", None),
        ("post", f"/friends/block/{UNKNOWN_USER_ID}", None),
        ("delete", f"/friends/block/{UNKNOWN_USER_ID}", None),
    )

    @pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
    async def test_requires_authentication(self, anon_with_csrf, method, path, body):
        kwargs = {"json": body} if body else {}

        response = await getattr(anon_with_csrf, method)(path, **kwargs)

        assert response.status_code == 401

    @pytest.mark.parametrize(
        ("method", "path", "body"),
        [endpoint for endpoint in ENDPOINTS if endpoint[0] != "get"],
    )
    async def test_mutations_require_csrf_token(self, alice_client, method, path, body):
        del alice_client.headers["X-CSRF-Token"]
        kwargs = {"json": body} if body else {}

        response = await getattr(alice_client, method)(path, **kwargs)

        assert response.status_code == 403
        assert response.json() == {"detail": "CSRF token missing"}


class TestListFriends:
    async def test_empty_by_default(self, alice_client):
        response = await alice_client.get("/friends")

        assert response.status_code == 200
        assert response.json() == {"friends": []}

    async def test_returns_public_fields_only(
        self, alice_client, alice, bob, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)

        response = await alice_client.get("/friends")

        assert response.json() == {
            "friends": [
                {
                    "id": user_uuid(bob),
                    "username": "bob",
                    "avatar_url": None,
                    "is_online": False,
                    "last_seen_at": None,
                }
            ]
        }

    async def test_includes_friends_from_both_directions(
        self, alice_client, alice, bob, carol, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)
        await make_friendship(carol, alice, FriendshipStatus.ACCEPTED)

        response = await alice_client.get("/friends")

        assert usernames(response.json()["friends"]) == {"bob", "carol"}

    @pytest.mark.parametrize(
        "status", [FriendshipStatus.PENDING, FriendshipStatus.BLOCKED]
    )
    async def test_excludes_non_accepted(
        self, alice_client, alice, bob, make_friendship, status
    ):
        await make_friendship(alice, bob, status)

        response = await alice_client.get("/friends")

        assert response.json() == {"friends": []}

    async def test_excludes_other_peoples_friendships(
        self, alice_client, bob, carol, make_friendship
    ):
        await make_friendship(bob, carol, FriendshipStatus.ACCEPTED)

        response = await alice_client.get("/friends")

        assert response.json() == {"friends": []}


class TestListPendingRequests:
    async def test_empty_by_default(self, alice_client):
        response = await alice_client.get("/friends/requests")

        assert response.status_code == 200
        assert response.json() == {"incoming": [], "outgoing": []}

    async def test_separates_incoming_and_outgoing(
        self, alice_client, alice, bob, carol, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.PENDING)
        await make_friendship(carol, alice, FriendshipStatus.PENDING)

        body = (await alice_client.get("/friends/requests")).json()

        assert usernames(body["outgoing"]) == {"bob"}
        assert usernames(body["incoming"]) == {"carol"}

    async def test_excludes_non_pending(
        self, alice_client, alice, bob, carol, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)
        await make_friendship(carol, alice, FriendshipStatus.BLOCKED)

        body = (await alice_client.get("/friends/requests")).json()

        assert body == {"incoming": [], "outgoing": []}


class TestSendFriendRequest:
    async def test_by_username(self, alice_client, alice, bob):
        response = await alice_client.post(
            "/friends/requests",
            json={"username": "bob"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["requester_id"] == user_uuid(alice)
        assert body["addressee_id"] == user_uuid(bob)
        assert body["status"] == "PENDING"
        assert body["id"] > 0
        assert body["created_at"] and body["updated_at"]

    async def test_by_user_id(self, alice_client, bob):
        response = await alice_client.post(
            "/friends/requests",
            json={"target_user_id": user_uuid(bob)},
        )

        assert response.status_code == 201
        assert response.json()["addressee_id"] == user_uuid(bob)

    async def test_is_visible_to_both_users(self, alice_client, bob_client, bob):
        await alice_client.post("/friends/requests", json={"username": "bob"})

        sender = (await alice_client.get("/friends/requests")).json()
        receiver = (await bob_client.get("/friends/requests")).json()

        assert usernames(sender["outgoing"]) == {"bob"}
        assert usernames(receiver["incoming"]) == {"alice"}

    async def test_user_id_wins_when_both_targets_are_given(
        self, alice_client, bob, carol
    ):
        response = await alice_client.post(
            "/friends/requests",
            json={"target_user_id": user_uuid(bob), "username": carol.username},
        )

        assert response.json()["addressee_id"] == user_uuid(bob)

    @pytest.mark.parametrize(
        "payload",
        [{}, {"username": ""}, {"target_user_id": ""}, {"username": None}],
    )
    async def test_target_is_required(self, alice_client, payload):
        response = await alice_client.post("/friends/requests", json=payload)

        assert response.status_code == 422
        assert response.json() == {"detail": "Provide a target user ID or username."}

    async def test_malformed_user_id_is_rejected(self, alice_client):
        response = await alice_client.post(
            "/friends/requests",
            json={"target_user_id": "not-a-uuid"},
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid user identifier"}

    @pytest.mark.parametrize(
        "payload",
        [{"username": "ghost"}, {"target_user_id": UNKNOWN_USER_ID}],
    )
    async def test_unknown_target_is_not_found(self, alice_client, payload):
        response = await alice_client.post("/friends/requests", json=payload)

        assert response.status_code == 404
        assert response.json() == {"detail": "Target user not found"}

    async def test_cannot_friend_yourself(self, alice_client, session_maker):
        response = await alice_client.post(
            "/friends/requests",
            json={"username": "alice"},
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Cannot send a friend request to yourself"}
        assert await count_friendships(session_maker) == 0

    async def test_duplicate_request_is_rejected(self, alice_client, bob):
        await alice_client.post("/friends/requests", json={"username": "bob"})

        response = await alice_client.post(
            "/friends/requests",
            json={"username": "bob"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Friendship relationship already exists with status: PENDING"
        }

    async def test_reverse_request_is_rejected(
        self, alice_client, alice, bob, make_friendship, session_maker
    ):
        await make_friendship(bob, alice, FriendshipStatus.PENDING)

        response = await alice_client.post(
            "/friends/requests",
            json={"username": "bob"},
        )

        assert response.status_code == 400
        assert await count_friendships(session_maker) == 1

    async def test_cannot_request_when_already_friends(
        self, alice_client, alice, bob, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)

        response = await alice_client.post(
            "/friends/requests",
            json={"username": "bob"},
        )

        assert response.status_code == 400
        assert "ACCEPTED" in response.json()["detail"]

    async def test_blocked_user_cannot_send_request(
        self, bob_client, alice, bob, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.BLOCKED)

        response = await bob_client.post(
            "/friends/requests",
            json={"username": "alice"},
        )

        assert response.status_code == 400


class TestHandleFriendRequest:
    async def test_accept(self, bob_client, alice, bob, make_friendship):
        request = await make_friendship(alice, bob, FriendshipStatus.PENDING)

        response = await bob_client.patch(
            f"/friends/requests/{request.id}",
            json={"action": "ACCEPTED"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == request.id
        assert body["status"] == "ACCEPTED"
        assert body["requester_id"] == user_uuid(alice)
        assert body["addressee_id"] == user_uuid(bob)

    async def test_accepted_users_become_friends_on_both_sides(
        self, alice_client, bob_client, alice, bob, make_friendship
    ):
        request = await make_friendship(alice, bob, FriendshipStatus.PENDING)

        await bob_client.patch(
            f"/friends/requests/{request.id}",
            json={"action": "ACCEPTED"},
        )

        alice_friends = (await alice_client.get("/friends")).json()["friends"]
        bob_friends = (await bob_client.get("/friends")).json()["friends"]
        assert usernames(alice_friends) == {"bob"}
        assert usernames(bob_friends) == {"alice"}
        assert (await bob_client.get("/friends/requests")).json()["incoming"] == []

    async def test_decline_removes_the_request(
        self, bob_client, alice, bob, make_friendship, session_maker
    ):
        request = await make_friendship(alice, bob, FriendshipStatus.PENDING)

        response = await bob_client.patch(
            f"/friends/requests/{request.id}",
            json={"action": "DECLINED"},
        )

        assert response.status_code == 200
        assert response.json() == {"detail": "Friend request declined and removed"}
        assert await count_friendships(session_maker) == 0

    async def test_can_request_again_after_decline(
        self, alice_client, bob_client, alice, bob, make_friendship
    ):
        request = await make_friendship(alice, bob, FriendshipStatus.PENDING)
        await bob_client.patch(
            f"/friends/requests/{request.id}",
            json={"action": "DECLINED"},
        )

        response = await alice_client.post(
            "/friends/requests",
            json={"username": "bob"},
        )

        assert response.status_code == 201

    async def test_requester_cannot_accept_own_request(
        self, alice_client, alice, bob, make_friendship, session_maker
    ):
        request = await make_friendship(alice, bob, FriendshipStatus.PENDING)

        response = await alice_client.patch(
            f"/friends/requests/{request.id}",
            json={"action": "ACCEPTED"},
        )

        assert response.status_code == 404
        stored = await get_friendship(session_maker, request.id)
        assert stored.status == FriendshipStatus.PENDING

    async def test_third_party_cannot_act_on_request(
        self, carol_client, alice, bob, make_friendship, session_maker
    ):
        request = await make_friendship(alice, bob, FriendshipStatus.PENDING)

        response = await carol_client.patch(
            f"/friends/requests/{request.id}",
            json={"action": "DECLINED"},
        )

        assert response.status_code == 404
        assert await get_friendship(session_maker, request.id) is not None

    async def test_unknown_request_is_not_found(self, alice_client):
        response = await alice_client.patch(
            "/friends/requests/999999",
            json={"action": "ACCEPTED"},
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Friend request not found or not addressed to you"
        }

    @pytest.mark.parametrize(
        "status", [FriendshipStatus.ACCEPTED, FriendshipStatus.BLOCKED]
    )
    async def test_only_pending_requests_can_be_handled(
        self, bob_client, alice, bob, make_friendship, status
    ):
        friendship = await make_friendship(alice, bob, status)

        response = await bob_client.patch(
            f"/friends/requests/{friendship.id}",
            json={"action": "ACCEPTED"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": f"Cannot process request with status: {status.value}"
        }

    @pytest.mark.parametrize("action", ["PENDING", "BLOCKED", "accepted", ""])
    async def test_invalid_action_is_rejected(self, alice_client, action):
        response = await alice_client.patch(
            "/friends/requests/1",
            json={"action": action},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "Value is invalid."}

    async def test_non_integer_request_id_is_rejected(self, alice_client):
        response = await alice_client.patch(
            "/friends/requests/abc",
            json={"action": "ACCEPTED"},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "Request ID is invalid."}


class TestRemoveFriend:
    async def test_removes_friend_for_both_users(
        self, alice_client, bob_client, alice, bob, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)

        response = await alice_client.delete(f"/friends/{user_uuid(bob)}")

        assert response.status_code == 200
        assert response.json() == {"detail": "Friend successfully removed"}
        assert (await alice_client.get("/friends")).json() == {"friends": []}
        assert (await bob_client.get("/friends")).json() == {"friends": []}

    async def test_addressee_can_remove_too(
        self, bob_client, alice, bob, make_friendship, session_maker
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)

        response = await bob_client.delete(f"/friends/{user_uuid(alice)}")

        assert response.status_code == 200
        assert await count_friendships(session_maker) == 0

    @pytest.mark.parametrize(
        "status", [FriendshipStatus.PENDING, FriendshipStatus.BLOCKED]
    )
    async def test_non_accepted_relationship_is_kept(
        self, alice_client, alice, bob, make_friendship, session_maker, status
    ):
        await make_friendship(alice, bob, status)

        response = await alice_client.delete(f"/friends/{user_uuid(bob)}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Accepted friend relationship not found"}
        assert await count_friendships(session_maker) == 1

    async def test_stranger_is_not_found(self, alice_client, bob):
        response = await alice_client.delete(f"/friends/{user_uuid(bob)}")

        assert response.status_code == 404

    async def test_malformed_id_is_rejected(self, alice_client):
        response = await alice_client.delete("/friends/not-a-uuid")

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid user identifier"}


class TestBlockUser:
    @pytest.mark.parametrize(
        "status", [FriendshipStatus.PENDING, FriendshipStatus.ACCEPTED]
    )
    async def test_converts_existing_relationship(
        self, alice_client, alice, bob, make_friendship, session_maker, status
    ):
        friendship = await make_friendship(alice, bob, status)

        response = await alice_client.post(f"/friends/block/{user_uuid(bob)}")

        assert response.status_code == 200
        assert response.json()["id"] == friendship.id
        assert response.json()["status"] == "BLOCKED"
        assert await count_friendships(session_maker) == 1

    async def test_blocker_becomes_requester(
        self, alice_client, alice, bob, make_friendship
    ):
        await make_friendship(bob, alice, FriendshipStatus.ACCEPTED)

        body = (await alice_client.post(f"/friends/block/{user_uuid(bob)}")).json()

        assert body["requester_id"] == user_uuid(alice)
        assert body["addressee_id"] == user_uuid(bob)

    async def test_blocked_friend_disappears_from_friend_lists(
        self, alice_client, bob_client, alice, bob, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)

        await alice_client.post(f"/friends/block/{user_uuid(bob)}")

        assert (await alice_client.get("/friends")).json() == {"friends": []}
        assert (await bob_client.get("/friends")).json() == {"friends": []}

    async def test_cannot_block_yourself(self, alice_client, alice):
        response = await alice_client.post(f"/friends/block/{user_uuid(alice)}")

        assert response.status_code == 400
        assert response.json() == {"detail": "Cannot block yourself"}

    async def test_malformed_id_is_rejected(self, alice_client):
        response = await alice_client.post("/friends/block/not-a-uuid")

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid user identifier"}

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: block_user calls friend_repo.create(requester_id=..., ...) but "
        "BaseRepository.create takes an entity, so TypeError gives a 500.",
    )
    async def test_blocks_a_user_with_no_prior_relationship(
        self, alice_client, alice, bob
    ):
        response = await alice_client.post(f"/friends/block/{user_uuid(bob)}")

        assert response.status_code == 200
        body = response.json()
        assert body["requester_id"] == user_uuid(alice)
        assert body["addressee_id"] == user_uuid(bob)
        assert body["status"] == "BLOCKED"

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: block_user never checks that the target exists, unlike "
        "send_friend_request which returns 404.",
    )
    async def test_blocking_unknown_user_is_not_found(self, alice_client):
        response = await alice_client.post(f"/friends/block/{UNKNOWN_USER_ID}")

        assert response.status_code == 404

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: blocking back overwrites the existing row's requester, so a "
        "blocked user can take over the block and then delete it.",
    )
    async def test_blocked_user_cannot_lift_the_block(
        self, alice_client, bob_client, alice, bob, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.BLOCKED)

        await bob_client.post(f"/friends/block/{user_uuid(alice)}")
        await bob_client.delete(f"/friends/block/{user_uuid(alice)}")

        # Alice's original block must still exist for Alice to remove.
        response = await alice_client.delete(f"/friends/block/{user_uuid(bob)}")
        assert response.status_code == 200


class TestUnblockUser:
    async def test_blocker_can_unblock(
        self, alice_client, alice, bob, make_friendship, session_maker
    ):
        await make_friendship(alice, bob, FriendshipStatus.BLOCKED)

        response = await alice_client.delete(f"/friends/block/{user_uuid(bob)}")

        assert response.status_code == 200
        assert response.json() == {"detail": "User successfully unblocked"}
        assert await count_friendships(session_maker) == 0

    async def test_blocked_user_cannot_unblock_themselves(
        self, bob_client, alice, bob, make_friendship, session_maker
    ):
        await make_friendship(alice, bob, FriendshipStatus.BLOCKED)

        response = await bob_client.delete(f"/friends/block/{user_uuid(alice)}")

        assert response.status_code == 404
        assert await count_friendships(session_maker) == 1

    async def test_non_blocked_relationship_is_kept(
        self, alice_client, alice, bob, make_friendship, session_maker
    ):
        await make_friendship(alice, bob, FriendshipStatus.ACCEPTED)

        response = await alice_client.delete(f"/friends/block/{user_uuid(bob)}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Blocked user record not found"}
        assert await count_friendships(session_maker) == 1

    async def test_no_relationship_is_not_found(self, alice_client, bob):
        response = await alice_client.delete(f"/friends/block/{user_uuid(bob)}")

        assert response.status_code == 404

    async def test_malformed_id_is_rejected(self, alice_client):
        response = await alice_client.delete("/friends/block/not-a-uuid")

        assert response.status_code == 400

    async def test_can_send_request_after_unblock(
        self, alice_client, alice, bob, make_friendship
    ):
        await make_friendship(alice, bob, FriendshipStatus.BLOCKED)
        await alice_client.delete(f"/friends/block/{user_uuid(bob)}")

        response = await alice_client.post(
            "/friends/requests",
            json={"username": "bob"},
        )

        assert response.status_code == 201
