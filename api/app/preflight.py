"""Deployment-time environment validation with safe, actionable output."""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlparse


PLACEHOLDERS = (
    "changeme",
    "replace-with",
    "user:pass@cluster.mongodb.net",
    "example.com",
)


def _value(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _safe_mongo_target(uri: str) -> str:
    """Redact MongoDB user info before printing the deployment target."""
    return re.sub(r"^(mongodb(?:\+srv)?://)[^/@]+@", r"\1***:***@", uri)


def validate_environment() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    password = _value("ADMIN_PASSWORD")
    if not password:
        errors.append("ADMIN_PASSWORD is missing")
    elif len(password) < 8:
        errors.append("ADMIN_PASSWORD must be at least 8 characters")
    elif "changeme" in password.lower():
        errors.append("ADMIN_PASSWORD still uses the insecure example value")

    encryption_key = _value("APP_ENCRYPTION_KEY")
    if not encryption_key:
        errors.append("APP_ENCRYPTION_KEY is missing")
    elif len(encryption_key.encode("utf-8")) < 32:
        errors.append("APP_ENCRYPTION_KEY must be at least 32 bytes")
    elif any(marker in encryption_key.lower() for marker in ("replace-with", "changeme")):
        errors.append("APP_ENCRYPTION_KEY still uses an example value")

    mongo_uri = _value("MONGODB_URI")
    if not mongo_uri:
        errors.append("MONGODB_URI is missing")
    elif not mongo_uri.startswith(("mongodb://", "mongodb+srv://")):
        errors.append("MONGODB_URI must start with mongodb:// or mongodb+srv://")
    elif any(marker in mongo_uri.lower() for marker in PLACEHOLDERS):
        errors.append("MONGODB_URI still contains an example hostname or credentials")

    if not _value("MONGODB_DB", "DTP"):
        errors.append("MONGODB_DB is empty")
    if not _value("MONGODB_COLLECTION_PREFIX", "tunes_"):
        errors.append("MONGODB_COLLECTION_PREFIX is empty")

    public_url = _value("APP_PUBLIC_URL", "http://localhost:8080")
    parsed_url = urlparse(public_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        errors.append("APP_PUBLIC_URL must be an absolute http:// or https:// URL")

    apple = {
        "APPLE_MUSIC_TEAM_ID": _value("APPLE_MUSIC_TEAM_ID"),
        "APPLE_MUSIC_KEY_ID": _value("APPLE_MUSIC_KEY_ID"),
        "APPLE_MUSIC_PRIVATE_KEY": _value("APPLE_MUSIC_PRIVATE_KEY"),
    }
    configured_apple = [name for name, value in apple.items() if value]
    if configured_apple and len(configured_apple) != len(apple):
        missing = ", ".join(name for name, value in apple.items() if not value)
        warnings.append(f"Apple Music playlist import is incomplete; missing {missing}")
    elif not configured_apple:
        warnings.append("Apple Music credentials are absent; playlist import will be unavailable")

    google = {
        "GOOGLE_OAUTH_CLIENT_ID": _value("GOOGLE_OAUTH_CLIENT_ID"),
        "GOOGLE_OAUTH_CLIENT_SECRET": _value("GOOGLE_OAUTH_CLIENT_SECRET"),
    }
    configured_google = [name for name, value in google.items() if value]
    if configured_google and len(configured_google) != len(google):
        missing = ", ".join(name for name, value in google.items() if not value)
        warnings.append(f"YouTube playlist import is incomplete; missing {missing}")
    elif not configured_google:
        warnings.append("Google OAuth credentials are absent; YouTube playlist import will be unavailable")

    return errors, warnings


def main() -> int:
    errors, warnings = validate_environment()
    print("dtp-tunes environment preflight")
    print(
        "Mongo target: "
        f"{_safe_mongo_target(_value('MONGODB_URI', '<missing>'))}/{_value('MONGODB_DB', 'DTP')} "
        f"(prefix: {_value('MONGODB_COLLECTION_PREFIX', 'tunes_')})"
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(f"Preflight failed with {len(errors)} configuration error(s).", file=sys.stderr)
        return 1
    print("Preflight passed: required environment is configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
