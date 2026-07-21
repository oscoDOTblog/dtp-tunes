"""Shared FastAPI dependencies: DB access and web-session authentication."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings, get_settings
from app.db import PrefixedDatabase, get_database
from app.repositories import sessions as sessions_repo
from app.repositories import users as users_repo


def get_db() -> PrefixedDatabase:
    return get_database()


async def _resolve_session_user(db: AsyncIOMotorDatabase, token: str | None) -> dict | None:
    if not token:
        return None
    session = await sessions_repo.get_session_by_token(db, token)
    if not session:
        return None
    user = await users_repo.get_user_by_id(db, session["userId"])
    if not user or not user.get("isActive", True):
        return None
    return user


async def require_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    token = request.cookies.get(settings.session_cookie_name)
    user = await _resolve_session_user(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


async def get_optional_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict | None:
    token = request.cookies.get(settings.session_cookie_name)
    return await _resolve_session_user(db, token)


async def require_admin(user: dict = Depends(require_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
