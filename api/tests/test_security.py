"""Tests for Argon2id password hashing, AES-GCM secret encryption, and Subsonic MD5 auth."""

from __future__ import annotations

from app import security


def test_password_hash_roundtrip():
    hashed = security.hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert security.verify_password(hashed, "correct-horse-battery-staple") is True
    assert security.verify_password(hashed, "wrong-password") is False


def test_password_hash_is_unique_per_call():
    a = security.hash_password("same-password")
    b = security.hash_password("same-password")
    assert a != b  # Argon2id salts each hash


def test_encrypt_decrypt_secret_roundtrip():
    plaintext = security.generate_subsonic_secret()
    encrypted = security.encrypt_secret(plaintext)
    assert encrypted.ciphertext_b64 != plaintext
    decrypted = security.decrypt_secret(encrypted)
    assert decrypted == plaintext


def test_encrypt_secret_produces_different_ciphertext_each_time():
    plaintext = "same-secret-value"
    first = security.encrypt_secret(plaintext)
    second = security.encrypt_secret(plaintext)
    assert first.ciphertext_b64 != second.ciphertext_b64  # random nonce each call
    assert security.decrypt_secret(first) == security.decrypt_secret(second) == plaintext


def test_encrypted_secret_doc_roundtrip():
    plaintext = "roundtrip-secret"
    encrypted = security.encrypt_secret(plaintext)
    doc = encrypted.to_doc()
    restored = security.EncryptedSecret.from_doc(doc)
    assert security.decrypt_secret(restored) == plaintext


def test_subsonic_legacy_token_scheme():
    password = "hunter2"
    salt = "c19b2d"
    expected_token = security.md5_hex(password + salt)
    # A client computing t = MD5(password + salt) must match our verification helper.
    assert security.constant_time_equals(expected_token, security.md5_hex(password + salt))
    assert not security.constant_time_equals(expected_token, security.md5_hex("wrong" + salt))


def test_new_opaque_id_is_unique_and_stable_format():
    a = security.new_opaque_id()
    b = security.new_opaque_id()
    assert a != b
    assert len(a) == 32  # uuid4 hex, no dashes


def test_normalize_username():
    assert security.normalize_username("  Alice ") == "alice"
    assert security.normalize_username("BOB") == "bob"
