"""Tests for avatar upload and the default avatar.

Uses the fixtures in tests/conftest.py from the backend API test suite.
"""

import re
import uuid

import pytest

# This suite lives on backend/api-tests, which may not contain avatars yet.
# Skip instead of failing collection until they are merged in.
pytest.importorskip(
    "backend.core.avatars", reason="Avatars are not merged into this branch"
)

from backend.core.config import settings
from backend.models import User

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
GIF = b"GIF89a" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 64


def uid(user: User) -> str:
    return str(uuid.UUID(bytes=user.id))


@pytest.fixture(autouse=True)
def media_dir(tmp_path, monkeypatch):
    path = tmp_path / "media"
    monkeypatch.setattr(settings, "MEDIA_DIR", str(path))
    return path


async def upload(client, data: bytes, filename="avatar.png", content_type="image/png"):
    return await client.put(
        "/users/me/avatar", files={"file": (filename, data, content_type)}
    )


class TestDefaultAvatar:
    async def test_user_without_avatar_gets_the_default(self, alice_client, alice):
        response = await alice_client.get(f"/users/{uid(alice)}/avatar")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.content.startswith(b"<svg")

    async def test_profile_avatar_url_stays_empty(self, alice_client):
        assert (await alice_client.get("/users/me")).json()["avatar_url"] is None


class TestUpload:
    @pytest.mark.parametrize(
        ("data", "media_type"),
        [
            (PNG, "image/png"),
            (JPEG, "image/jpeg"),
            (GIF, "image/gif"),
            (b"GIF87a" + b"\x00" * 8, "image/gif"),
            (WEBP, "image/webp"),
        ],
    )
    async def test_supported_images(self, alice_client, alice, data, media_type):
        response = await upload(alice_client, data)

        assert response.status_code == 200
        served = await alice_client.get(f"/users/{uid(alice)}/avatar")
        assert served.status_code == 200
        assert served.headers["content-type"] == media_type
        assert served.headers["x-content-type-options"] == "nosniff"
        assert served.content == data

    async def test_sets_a_versioned_avatar_url(self, alice_client, alice):
        response = await upload(alice_client, PNG)

        url = response.json()["avatar_url"]
        assert re.fullmatch(
            rf"/api/v1/users/{uid(alice)}/avatar\?v=[0-9a-f]{{12}}", url
        )
        assert (await alice_client.get("/users/me")).json()["avatar_url"] == url

    async def test_replacing_changes_the_url_and_file(
        self, alice_client, alice, media_dir
    ):
        first = (await upload(alice_client, PNG)).json()["avatar_url"]
        second = (await upload(alice_client, JPEG)).json()["avatar_url"]

        assert first != second
        assert sorted(p.name for p in (media_dir / "avatars").iterdir()) == [
            f"{uid(alice)}.jpg"
        ]

    async def test_file_is_named_after_the_user(self, alice_client, alice, media_dir):
        await upload(alice_client, PNG, filename="../../../etc/evil.png")

        assert [p.name for p in (media_dir / "avatars").iterdir()] == [
            f"{uid(alice)}.png"
        ]
        assert not (media_dir.parent / "etc").exists()

    async def test_other_users_can_see_it(self, alice_client, bob_client, alice):
        await upload(alice_client, PNG)

        response = await bob_client.get(f"/users/{uid(alice)}/avatar")

        assert response.status_code == 200
        assert response.content == PNG

    @pytest.mark.parametrize(
        ("data", "content_type"),
        [
            (b"<html><script>alert(1)</script></html>", "image/png"),
            (b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', "image/svg+xml"),
            (b"just some text", "text/plain"),
            (b"", "image/png"),
            (b"\x89PN", "image/png"),
        ],
        ids=["html-disguised-as-png", "svg", "text", "empty", "truncated"],
    )
    async def test_rejects_non_images(
        self, alice_client, media_dir, data, content_type
    ):
        response = await upload(alice_client, data, content_type=content_type)

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Avatar must be a PNG, JPEG, WebP or GIF image."
        }
        assert not (media_dir / "avatars").exists()

    async def test_rejects_large_files(self, alice_client, monkeypatch, media_dir):
        monkeypatch.setattr(settings, "AVATAR_MAX_BYTES", 2 * 1024 * 1024)

        response = await upload(alice_client, PNG + b"\x00" * (2 * 1024 * 1024))

        assert response.status_code == 413
        assert response.json() == {"detail": "Avatar must be at most 2 MB."}
        assert not (media_dir / "avatars").exists()

    async def test_accepts_a_file_at_the_limit(self, alice_client, monkeypatch):
        monkeypatch.setattr(settings, "AVATAR_MAX_BYTES", len(PNG))

        assert (await upload(alice_client, PNG)).status_code == 200

    async def test_missing_file(self, alice_client):
        response = await alice_client.put("/users/me/avatar")

        assert response.status_code == 422

    async def test_requires_csrf(self, alice_client, media_dir):
        del alice_client.headers["X-CSRF-Token"]

        response = await upload(alice_client, PNG)

        assert response.status_code == 403
        assert not (media_dir / "avatars").exists()

    async def test_requires_authentication(self, anon_with_csrf):
        assert (await upload(anon_with_csrf, PNG)).status_code == 401


class TestRemove:
    async def test_falls_back_to_the_default(self, alice_client, alice, media_dir):
        await upload(alice_client, PNG)

        response = await alice_client.delete("/users/me/avatar")

        assert response.status_code == 200
        assert response.json()["avatar_url"] is None
        assert list((media_dir / "avatars").iterdir()) == []
        served = await alice_client.get(f"/users/{uid(alice)}/avatar")
        assert served.headers["content-type"] == "image/svg+xml"

    async def test_without_an_avatar(self, alice_client):
        response = await alice_client.delete("/users/me/avatar")

        assert response.status_code == 200

    async def test_requires_csrf(self, alice_client):
        del alice_client.headers["X-CSRF-Token"]

        assert (await alice_client.delete("/users/me/avatar")).status_code == 403


class TestServe:
    async def test_external_avatar_redirects(self, alice_client, bob_client, alice):
        await alice_client.patch(
            "/users/me", json={"avatar_url": "https://lh3.googleusercontent.com/a/x"}
        )

        response = await bob_client.get(f"/users/{uid(alice)}/avatar")

        assert response.status_code == 307
        assert response.headers["location"] == "https://lh3.googleusercontent.com/a/x"

    async def test_unknown_user(self, alice_client):
        response = await alice_client.get(f"/users/{uuid.uuid4()}/avatar")

        assert response.status_code == 404

    async def test_requires_authentication(self, client, alice):
        response = await client.get(f"/users/{uid(alice)}/avatar")

        assert response.status_code == 401

    async def test_deleting_the_user_deletes_the_file(
        self, alice_client, alice, make_user, login_as, media_dir
    ):
        from backend.models import UserRole

        await upload(alice_client, PNG)
        gm_client = await login_as(await make_user(role=UserRole.GAME_MASTER))

        await gm_client.delete(f"/admin/users/{uid(alice)}")

        assert list((media_dir / "avatars").iterdir()) == []
