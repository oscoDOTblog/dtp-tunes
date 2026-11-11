"""Admin user management: role changes and password resets for other users."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.deps import get_db, require_admin, require_user
from app.main import app
from app.security import hash_password, verify_password


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return list(self._docs)


class _FakeCollection:
    def __init__(self):
        self.docs = {}

    def _matches(self, doc, filt):
        return all(doc.get(k) == v for k, v in filt.items())

    async def find_one(self, filt):
        for doc in self.docs.values():
            if self._matches(doc, filt):
                return dict(doc)
        return None

    def find(self, filt=None):
        filt = filt or {}
        return _FakeCursor([dict(d) for d in self.docs.values() if self._matches(d, filt)])

    async def update_one(self, filt, update):
        for _id, doc in self.docs.items():
            if self._matches(doc, filt):
                updated = dict(doc)
                updated.update(update.get("$set", {}))
                self.docs[_id] = updated
                return

    async def delete_many(self, filt):
        for _id in [i for i, d in self.docs.items() if self._matches(d, filt)]:
            del self.docs[_id]


class _FakeDB:
    def __init__(self):
        self.users = _FakeCollection()
        self.sessions = _FakeCollection()


def _user(_id, username, role):
    return {
        "_id": _id,
        "username": username,
        "normalizedUsername": username.lower(),
        "passwordHash": hash_password("old-password-123"),
        "role": role,
        "isActive": True,
        "createdAt": "2026-01-01T00:00:00+00:00",
        "updatedAt": "2026-01-01T00:00:00+00:00",
    }


def _client_as(db, admin):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_admin] = lambda: admin
    return TestClient(app)


def test_admin_password_reset_updates_hash_and_signs_out_user():
    db = _FakeDB()
    admin = _user("admin1", "boss", "admin")
    bob = _user("user2", "bob", "user")
    db.users.docs = {"admin1": admin, "user2": bob}
    db.sessions.docs = {"sess1": {"_id": "sess1", "userId": "user2"}}
    client = _client_as(db, admin)
    try:
        response = client.patch("/api/admin/users/user2/password", json={"password": "brand-new-password"})
        assert response.status_code == 200, response.text
        assert verify_password(db.users.docs["user2"]["passwordHash"], "brand-new-password")
        assert db.sessions.docs == {}
        # The admin performing the reset stays signed in (their sessions untouched).
        assert "admin1" in db.users.docs
    finally:
        app.dependency_overrides.clear()


def test_admin_password_reset_keeps_own_session():
    db = _FakeDB()
    admin = _user("admin1", "boss", "admin")
    db.users.docs = {"admin1": admin}
    db.sessions.docs = {"sess9": {"_id": "sess9", "userId": "admin1"}}
    client = _client_as(db, admin)
    try:
        response = client.patch("/api/admin/users/admin1/password", json={"password": "my-own-new-password"})
        assert response.status_code == 200, response.text
        assert verify_password(db.users.docs["admin1"]["passwordHash"], "my-own-new-password")
        assert "sess9" in db.sessions.docs
    finally:
        app.dependency_overrides.clear()


def test_admin_password_reset_rejects_unknown_user_and_short_password():
    db = _FakeDB()
    admin = _user("admin1", "boss", "admin")
    db.users.docs = {"admin1": admin}
    client = _client_as(db, admin)
    try:
        assert client.patch("/api/admin/users/missing/password", json={"password": "long-enough-password"}).status_code == 404
        short = client.patch("/api/admin/users/admin1/password", json={"password": "short"})
        assert short.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_admin_role_change_promotes_user():
    db = _FakeDB()
    admin = _user("admin1", "boss", "admin")
    bob = _user("user2", "bob", "user")
    db.users.docs = {"admin1": admin, "user2": bob}
    client = _client_as(db, admin)
    try:
        response = client.patch("/api/admin/users/user2/role", params={"role": "admin"})
        assert response.status_code == 200, response.text
        assert db.users.docs["user2"]["role"] == "admin"
    finally:
        app.dependency_overrides.clear()


def test_admin_cannot_change_own_role_or_remove_last_admin():
    db = _FakeDB()
    admin = _user("admin1", "boss", "admin")
    db.users.docs = {"admin1": admin}
    client = _client_as(db, admin)
    try:
        assert client.patch("/api/admin/users/admin1/role", params={"role": "user"}).status_code == 400
        assert db.users.docs["admin1"]["role"] == "admin"
    finally:
        app.dependency_overrides.clear()


def test_admin_role_and_password_endpoints_require_admin():
    app.dependency_overrides[require_user] = lambda: {"_id": "user2", "role": "user"}
    try:
        client = TestClient(app)
        assert client.patch("/api/admin/users/user2/role", params={"role": "admin"}).status_code == 403
        assert client.patch("/api/admin/users/user2/password", json={"password": "brand-new-password"}).status_code == 403
    finally:
        app.dependency_overrides.clear()
