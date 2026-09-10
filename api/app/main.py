"""FastAPI application entrypoint (`uvicorn app.main:app`)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import close_connection, ensure_indexes
from app.routes import api_admin, api_auth, api_library, api_media, api_player, api_playlists, health, subsonic
from app.services.auth_service import bootstrap_admin
from app.services.transfer_logging import TransferLoggingMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dtp_tunes.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await ensure_indexes()

    from app.db import get_database

    await bootstrap_admin(get_database(), username=settings.admin_username, password=settings.admin_password)
    logger.info("dtp-tunes API started")
    yield
    await close_connection()
    logger.info("dtp-tunes API stopped")


app = FastAPI(title="dtp-tunes API", version="0.1.0", lifespan=lifespan)

app.add_middleware(TransferLoggingMiddleware)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_auth.router)
app.include_router(api_library.router)
app.include_router(api_playlists.router)
app.include_router(api_player.router)
app.include_router(api_media.router)
app.include_router(api_admin.router)
app.include_router(api_admin.keys_router)
app.include_router(subsonic.router)
