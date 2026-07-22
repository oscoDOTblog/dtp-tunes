"""Web JSON auth: login, logout, current-user (cookie sessions for the Next.js app)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings, get_settings
from app.deps import get_db, require_user
from app.models import LoginRequest, SubsonicPasswordOut, UserOut
from app.repositories import sessions as sessions_repo
from app.security import new_session_token
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: dict) -> UserOut:
    return UserOut(
        id=user["_id"], username=user["username"], role=user["role"], isActive=user.get("isActive", True), createdAt=user["createdAt"]
    )


def _is_https(request: Request) -> bool:
    """Detect HTTPS after Traefik → nginx, using trusted X-Forwarded-Proto."""
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "")
    return forwarded.split(",")[0].strip().lower() == "https"


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserOut:
    user = await auth_service.authenticate_web_login(db, username=body.username, password=body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = new_session_token()
    await sessions_repo.create_session(
        db, user_id=user["_id"], token=token, ttl_seconds=settings.session_ttl_seconds, user_agent=request.headers.get("user-agent")
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=_is_https(request),
        path="/",
    )
    return _user_out(user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await sessions_repo.delete_session(db, token)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_is_https(request),
    )
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(require_user)) -> UserOut:
    return _user_out(user)


@router.get("/subsonic-password", response_model=SubsonicPasswordOut)
async def get_subsonic_password(user: dict = Depends(require_user)) -> SubsonicPasswordOut:
    """Reveal the Subsonic compatibility secret used as the client password."""
    try:
        password = auth_service.reveal_subsonic_secret(user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt Subsonic password — check APP_ENCRYPTION_KEY",
        ) from exc
    return SubsonicPasswordOut(username=user["username"], password=password, rotated=False)


@router.post("/subsonic-password/rotate", response_model=SubsonicPasswordOut)
async def rotate_subsonic_password(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
) -> SubsonicPasswordOut:
    """Replace the Subsonic compatibility secret (disconnects existing Subsonic clients)."""
    password = await auth_service.rotate_subsonic_secret(db, user)
    return SubsonicPasswordOut(username=user["username"], password=password, rotated=True)
