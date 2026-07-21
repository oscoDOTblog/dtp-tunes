"""Machine-to-machine ingest endpoints (VideoDL library handoff)."""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings, get_settings
from app.db import get_database
from app.repositories import scan_jobs as scan_jobs_repo

logger = logging.getLogger("dtp_tunes.ingest")

router = APIRouter(prefix="/api/internal", tags=["internal"])


def _require_ingest_token(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = (settings.dtp_tunes_ingest_token or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingest token is not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    provided = authorization[len("Bearer ") :].strip()
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest token")


@router.post("/scan")
async def trigger_ingest_scan(
    _: None = Depends(_require_ingest_token),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    doc = await scan_jobs_repo.enqueue_scan(db, triggered_by="videodl-ingest")
    logger.info("Ingest scan enqueued: %s", doc["_id"])
    return {"ok": True, "scanJobId": doc["_id"], "status": doc["status"]}
