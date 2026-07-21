"""Bootstrap, web login, API keys, and legacy Subsonic authentication."""

from __future__ import annotations

import logging
import secrets

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories import api_keys as api_keys_repo
from app.repositories import users as users_repo
from app.security import (
    EncryptedSecret,
    constant_time_equals,
    decrypt_secret,
    encrypt_secret,
    generate_subsonic_secret,
    hash_password,
    md5_hex,
    new_opaque_id,
    normalize_username,
    verify_password,
)

logger = logging.getLogger("dtp_tunes.auth")


async def bootstrap_admin(db: AsyncIOMotorDatabase, *, username: str, password: str) -> None:
    """Create the first admin account from env/secrets if no users exist yet."""
    existing_count = await users_repo.count_users(db)
    if existing_count > 0:
        return
    secret = encrypt_secret(generate_subsonic_secret())
    await users_repo.create_user(
        db,
        username=username,
        password_hash=hash_password(password),
        role="admin",
        subsonic_secret_encrypted=secret.to_doc(),
    )
    logger.info("Bootstrapped first admin user %r", username)


async def authenticate_web_login(db: AsyncIOMotorDatabase, *, username: str, password: str) -> dict | None:
    user = await users_repo.get_user_by_username(db, username)
    if not user or not user.get("isActive", True):
        return None
    if not verify_password(user["passwordHash"], password):
        return None
    return user


async def create_user_with_password(
    db: AsyncIOMotorDatabase, *, username: str, password: str, role: str
) -> dict:
    secret = encrypt_secret(generate_subsonic_secret())
    return await users_repo.create_user(
        db,
        username=username,
        password_hash=hash_password(password),
        role=role,
        subsonic_secret_encrypted=secret.to_doc(),
    )


def _subsonic_secret_of(user: dict) -> str:
    return decrypt_secret(EncryptedSecret.from_doc(user["subsonicSecretEncrypted"]))


async def authenticate_subsonic(
    db: AsyncIOMotorDatabase,
    *,
    username: str,
    token: str | None,
    salt: str | None,
    password: str | None,
    api_key: str | None,
) -> dict | None:
    """Supports Subsonic token/salt auth, legacy plaintext/hex password auth, and API keys."""
    if api_key:
        return await authenticate_api_key(db, api_key)

    user = await users_repo.get_user_by_username(db, username) if username else None
    if not user or not user.get("isActive", True):
        return None

    try:
        secret = _subsonic_secret_of(user)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to decrypt Subsonic secret for user %s", user["_id"])
        return None

    if token and salt:
        expected = md5_hex(secret + salt)
        if constant_time_equals(expected, token.lower()):
            return user
        return None

    if password:
        supplied = password
        if supplied.startswith("enc:"):
            try:
                supplied = bytes.fromhex(supplied[4:]).decode("utf-8")
            except ValueError:
                return None
        if constant_time_equals(supplied, secret):
            return user
        return None

    return None


async def authenticate_api_key(db: AsyncIOMotorDatabase, full_key: str) -> dict | None:
    from app.security import verify_password as verify_secret

    if "." not in full_key:
        return None
    key_id, _, secret = full_key.partition(".")
    record = await api_keys_repo.get_by_key_id(db, key_id)
    if not record:
        return None
    if not verify_secret(record["secretHash"], secret):
        return None
    user = await users_repo.get_user_by_id(db, record["userId"])
    if not user or not user.get("isActive", True):
        return None
    await api_keys_repo.touch_last_used(db, record["_id"])
    return user


async def create_api_key(db: AsyncIOMotorDatabase, *, user_id: str, name: str) -> tuple[dict, str]:
    key_id = new_opaque_id()[:16]
    secret = secrets.token_urlsafe(24)
    record = await api_keys_repo.create_api_key(
        db, user_id=user_id, key_id=key_id, secret_hash=hash_password(secret), name=name
    )
    full_key = f"{key_id}.{secret}"
    return record, full_key


def username_is_valid(username: str) -> bool:
    normalized = normalize_username(username)
    return 3 <= len(normalized) <= 64
