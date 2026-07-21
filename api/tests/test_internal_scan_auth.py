"""Auth tests for POST /api/internal/scan (router isolation, no Mongo lifespan)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("APP_ENCRYPTION_KEY", "test-only-encryption-key-32-bytes-minimum")
os.environ.setdefault("ADMIN_PASSWORD", "test-only-admin-password")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB", "DTP_test")
os.environ["DTP_TUNES_INGEST_TOKEN"] = "test-ingest-token"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_database
from app.routes import api_internal


def _make_client():
    get_settings.cache_clear()
    app = FastAPI()
    app.include_router(api_internal.router)

    async def _fake_db():
        return object()

    app.dependency_overrides[get_database] = _fake_db
    return TestClient(app)


def test_ingest_scan_requires_bearer():
    with _make_client() as client:
        response = client.post("/api/internal/scan")
        assert response.status_code == 401
    get_settings.cache_clear()


def test_ingest_scan_rejects_bad_token():
    with _make_client() as client:
        response = client.post(
            "/api/internal/scan",
            headers={"Authorization": "Bearer wrong"},
        )
        assert response.status_code == 401
    get_settings.cache_clear()


def test_ingest_scan_accepts_valid_token():
    with patch(
        "app.routes.api_internal.scan_jobs_repo.enqueue_scan",
        new_callable=AsyncMock,
    ) as enqueue:
        enqueue.return_value = {"_id": "scan1", "status": "queued"}
        with _make_client() as client:
            response = client.post(
                "/api/internal/scan",
                headers={"Authorization": "Bearer test-ingest-token"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["scanJobId"] == "scan1"
        enqueue.assert_awaited()
    get_settings.cache_clear()
