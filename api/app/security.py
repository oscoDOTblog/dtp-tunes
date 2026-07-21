"""Password hashing, session tokens, and reversible Subsonic-compat encryption.

Web passwords use Argon2id (argon2-cffi) and are never recoverable.

Legacy Subsonic clients (token/salt or plaintext password auth per the
Subsonic API) require the server to compare against the *original*
credential, which Argon2id hashing cannot support. To bridge this, every
user also gets a randomly generated "Subsonic compatibility secret" that is
stored reversibly using AES-256-GCM, encrypted with APP_ENCRYPTION_KEY. This
secret is unrelated to (and never derived from) the user's web password, so
even full decryption of every stored secret cannot recover a web login. This
tradeoff is documented in docs/SUBSONIC_COMPATIBILITY.md.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

_NONCE_LENGTH = 12


def hash_password(plain: str) -> str:
    return _password_hasher.hash(plain)


def verify_password(hashed: str, plain: str) -> bool:
    try:
        return _password_hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - malformed hash, treat as mismatch
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(hashed)
    except Exception:  # noqa: BLE001
        return False


def _derive_encryption_key() -> bytes:
    """Derive a 32-byte AES-256 key from APP_ENCRYPTION_KEY via SHA-256."""
    settings = get_settings()
    return hashlib.sha256(settings.app_encryption_key.encode("utf-8")).digest()


@dataclass(frozen=True)
class EncryptedSecret:
    nonce_b64: str
    ciphertext_b64: str

    def to_doc(self) -> dict:
        return {"nonce": self.nonce_b64, "ciphertext": self.ciphertext_b64}

    @classmethod
    def from_doc(cls, doc: dict) -> "EncryptedSecret":
        return cls(nonce_b64=doc["nonce"], ciphertext_b64=doc["ciphertext"])


def generate_subsonic_secret() -> str:
    """A random, high-entropy legacy-compat credential (not the web password)."""
    return secrets.token_urlsafe(24)


def encrypt_secret(plaintext: str) -> EncryptedSecret:
    import base64

    key = _derive_encryption_key()
    nonce = os.urandom(_NONCE_LENGTH)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return EncryptedSecret(
        nonce_b64=base64.b64encode(nonce).decode("ascii"),
        ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
    )


def decrypt_secret(encrypted: EncryptedSecret) -> str:
    import base64

    key = _derive_encryption_key()
    aesgcm = AESGCM(key)
    nonce = base64.b64decode(encrypted.nonce_b64)
    ciphertext = base64.b64decode(encrypted.ciphertext_b64)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def md5_hex(value: str) -> str:
    """MD5 is required by the legacy Subsonic token scheme: t = MD5(password + salt)."""
    return hashlib.md5(value.encode("utf-8")).hexdigest()  # noqa: S324


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def new_opaque_id() -> str:
    """Stable opaque ID for Mongo documents (uuid4 hex, not ObjectId)."""
    import uuid

    return uuid.uuid4().hex


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Deterministic SHA-256 for high-entropy tokens (sessions, API key secrets lookup)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_username(username: str) -> str:
    return username.strip().lower()
