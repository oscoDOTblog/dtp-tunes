from __future__ import annotations

from fastapi import APIRouter

from app.db import ping
from app.models import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    mongo_ok = await ping()
    return HealthOut(status="ok" if mongo_ok else "degraded", mongodb=mongo_ok, version="0.1.0")
