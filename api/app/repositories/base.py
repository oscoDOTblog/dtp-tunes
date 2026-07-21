"""Shared repository helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())
