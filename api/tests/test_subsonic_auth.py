"""Tests for legacy Subsonic token/salt and password authentication against a fake DB."""

from __future__ import annotations

import pytest

from app import security
from app.services import auth_service


class _FakeCollection:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    async def find_one(self, query: dict):
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None


class _FakeDB:
    def __init__(self, users: list[dict]):
        self.users = _FakeCollection(users)


def _make_user(username: str, subsonic_secret: str) -> dict:
    encrypted = security.encrypt_secret(subsonic_secret)
    return {
        "_id": security.new_opaque_id(),
        "username": username,
        "normalizedUsername": security.normalize_username(username),
        "isActive": True,
        "role": "user",
        "subsonicSecretEncrypted": encrypted.to_doc(),
    }


@pytest.mark.asyncio
async def test_authenticate_subsonic_token_salt_success():
    secret = "s3cret-compat-value"
    user = _make_user("alice", secret)
    db = _FakeDB([user])

    salt = "abc123"
    token = security.md5_hex(secret + salt)

    result = await auth_service.authenticate_subsonic(db, username="alice", token=token, salt=salt, password=None, api_key=None)
    assert result is not None
    assert result["username"] == "alice"


@pytest.mark.asyncio
async def test_authenticate_subsonic_token_salt_wrong_token():
    secret = "s3cret-compat-value"
    user = _make_user("alice", secret)
    db = _FakeDB([user])

    result = await auth_service.authenticate_subsonic(
        db, username="alice", token="deadbeef", salt="abc123", password=None, api_key=None
    )
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_subsonic_legacy_password_success():
    secret = "legacy-plain-secret"
    user = _make_user("bob", secret)
    db = _FakeDB([user])

    result = await auth_service.authenticate_subsonic(db, username="bob", token=None, salt=None, password=secret, api_key=None)
    assert result is not None
    assert result["username"] == "bob"


@pytest.mark.asyncio
async def test_authenticate_subsonic_hex_encoded_password():
    secret = "legacy-plain-secret"
    user = _make_user("carol", secret)
    db = _FakeDB([user])

    hex_password = "enc:" + secret.encode("utf-8").hex()
    result = await auth_service.authenticate_subsonic(db, username="carol", token=None, salt=None, password=hex_password, api_key=None)
    assert result is not None
    assert result["username"] == "carol"


@pytest.mark.asyncio
async def test_authenticate_subsonic_unknown_user():
    db = _FakeDB([])
    result = await auth_service.authenticate_subsonic(db, username="ghost", token="x", salt="y", password=None, api_key=None)
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_subsonic_inactive_user_rejected():
    user = _make_user("dave", "some-secret")
    user["isActive"] = False
    db = _FakeDB([user])

    result = await auth_service.authenticate_subsonic(
        db, username="dave", token=None, salt=None, password="some-secret", api_key=None
    )
    assert result is None
