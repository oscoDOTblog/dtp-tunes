"""Admin-only download and upload endpoints for the Tunes music library."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import ipaddress
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from PIL import Image
from pydantic import BaseModel, Field

from app.config import get_settings
from app.deps import get_db, require_admin
from app.repositories import ingest_jobs, scan_jobs
from app.repositories.base import utcnow
from app.services.ingest import (
    MAX_COVER_BYTES, MAX_UPLOAD_BYTES, MAX_UPLOAD_FILES,
    cleanup_job, job_dir, promote_tracks, read_tags,
)

router = APIRouter(prefix="/api/admin/ingest", tags=["ingest"])


class AlbumInput(BaseModel):
    title: str = ""
    artist: str = ""
    year: str = ""


class MetadataInput(BaseModel):
    url: str


class JobInput(BaseModel):
    url: str
    mode: str
    album: AlbumInput
    coverBase64: str | None = None


class ReviewTrack(BaseModel):
    id: int
    title: str = Field(min_length=1, max_length=200)


class ReviewInput(BaseModel):
    tracks: list[ReviewTrack]


def _check_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="A public HTTP(S) media URL is required")
    host = parsed.hostname.lower()
    if host in {"localhost", "host.docker.internal"} or host.endswith(".local"):
        raise HTTPException(status_code=400, detail="Local URLs are not allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise HTTPException(status_code=400, detail="Local URLs are not allowed")
    return url.strip()


def _cover_bytes(data: str | None) -> bytes | None:
    if not data:
        return None
    try:
        decoded = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid cover image") from exc
    if len(decoded) > MAX_COVER_BYTES:
        raise HTTPException(status_code=413, detail="Cover exceeds 8 MiB")
    return _validate_cover(decoded)


def _validate_cover(data: bytes) -> bytes:
    from io import BytesIO
    try:
        image = Image.open(BytesIO(data))
        if image.format not in {"JPEG", "PNG"}:
            raise ValueError("Unsupported image format")
        image.verify()
        image = Image.open(BytesIO(data)).convert("RGB")
        output = BytesIO()
        image.save(output, format="JPEG", quality=92)
        return output.getvalue()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Cover must be a valid JPEG or PNG") from exc


async def _save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> None:
    size = 0
    with destination.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(status_code=413, detail=f"File exceeds limit: {upload.filename}")
            handle.write(chunk)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file")


@router.get("/status")
async def status(_: dict = Depends(require_admin)) -> dict:
    root = Path(get_settings().music_path)
    return {"musicMounted": root.is_dir(), "musicWritable": os.access(root, os.W_OK)}


@router.post("/metadata")
async def metadata(payload: MetadataInput, _: dict = Depends(require_admin)) -> dict:
    url = _check_url(payload.url)
    def inspect() -> dict:
        result = subprocess.run(
            ["yt-dlp", "--dump-single-json", "--skip-download", "--no-warnings", url],
            capture_output=True, text=True, timeout=90, check=False,
        )
        if result.returncode:
            raise HTTPException(status_code=400, detail=(result.stderr or "Unable to load metadata")[-1500:])
        return json.loads(result.stdout)
    try:
        data = await asyncio.to_thread(inspect)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Metadata lookup timed out") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Invalid metadata response") from exc
    return {
        "title": data.get("title") or data.get("playlist_title") or "",
        "artist": data.get("uploader") or data.get("channel") or data.get("creator") or "",
        "year": str(data.get("release_year") or data.get("upload_date") or "")[:4],
        "thumbnailUrl": data.get("thumbnail"),
    }


@router.post("/jobs")
async def create_job(payload: JobInput, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    if payload.mode not in {"oneOff", "queue"}:
        raise HTTPException(status_code=400, detail="Invalid job mode")
    url = _check_url(payload.url)
    cover = _cover_bytes(payload.coverBase64)
    job = await ingest_jobs.create(db, mode=payload.mode, url=url, album=payload.album.model_dump(), cover_name="cover.jpg" if cover else None)
    try:
        directory = job_dir(job["_id"])
        directory.mkdir(parents=True, exist_ok=True)
        if cover:
            (directory / "cover.jpg").write_bytes(cover)
    except OSError as exc:
        await db.ingestJobs.delete_one({"_id": job["_id"]})
        raise HTTPException(status_code=500, detail="Unable to stage download") from exc
    return ingest_jobs.public_job(await ingest_jobs.update(db, job["_id"], status="queued"))


@router.get("/jobs")
async def list_jobs(db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    return {"jobs": [ingest_jobs.public_job(job) for job in await ingest_jobs.list_recent(db)]}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    job = await ingest_jobs.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ingest_jobs.public_job(job)


@router.post("/jobs/{job_id}/save")
async def save_review(job_id: str, payload: ReviewInput, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    job = await ingest_jobs.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["mode"] != "oneOff" or job["status"] != "readyForReview":
        raise HTTPException(status_code=409, detail="Job is not ready for review")
    original = {track["id"]: track for track in job.get("tracks") or []}
    if not payload.tracks or set(track.id for track in payload.tracks) != set(original) or len(payload.tracks) != len(original):
        raise HTTPException(status_code=400, detail="Tracks must be an exact reordering")
    claimed = await db.ingestJobs.find_one_and_update(
        {"_id": job_id, "status": "readyForReview"}, {"$set": {"status": "saving", "updatedAt": utcnow()}},
    )
    if not claimed:
        raise HTTPException(status_code=409, detail="Job is already being saved")
    directory = job_dir(job_id)
    cover_path = directory / (job.get("coverName") or "source.jpg")
    cover = cover_path.read_bytes() if cover_path.is_file() else None
    try:
        await asyncio.to_thread(
            promote_tracks,
            [(directory / original[track.id]["filename"], track.title) for track in payload.tracks],
            artist=job["album"].get("artist") or "Unknown Artist",
            album=job["album"].get("title") or "Unknown Album",
            year=job["album"].get("year") or "", cover=cover,
        )
    except Exception:
        await ingest_jobs.update(db, job_id, status="readyForReview")
        raise
    scan_error = None
    try:
        await scan_jobs.enqueue_scan(db, triggered_by=f"ingest:{job_id}")
    except Exception as exc:
        scan_error = str(exc)[:500]
    updated = await ingest_jobs.update(db, job_id, status="completed", finishedAt=utcnow(), tracks=[], scanError=scan_error)
    cleanup_job(job_id)
    return ingest_jobs.public_job(updated)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    job = await ingest_jobs.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in ingest_jobs.TERMINAL or job["status"] == "saving":
        raise HTTPException(status_code=409, detail="Job cannot be cancelled")
    fields = {"cancelRequested": True}
    if job["status"] in {"queued", "readyForReview"}:
        fields.update(status="cancelled", finishedAt=utcnow())
        cleanup_job(job_id)
    return ingest_jobs.public_job(await ingest_jobs.update(db, job_id, **fields))


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    job = await ingest_jobs.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in {"failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Job cannot be retried")
    return ingest_jobs.public_job(await ingest_jobs.update(
        db, job_id, status="queued", cancelRequested=False, error=None,
        leaseOwner=None, leaseExpiresAt=None, finishedAt=None, retryCount=job.get("retryCount", 0) + 1,
    ))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    result = await db.ingestJobs.delete_one({"_id": job_id, "status": {"$in": list(ingest_jobs.TERMINAL)}})
    if not result.deleted_count:
        raise HTTPException(status_code=409, detail="Only finished jobs can be removed")
    cleanup_job(job_id)
    return {"ok": True}


@router.delete("/jobs")
async def clear_finished(db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    finished = await db.ingestJobs.find({"status": {"$in": list(ingest_jobs.TERMINAL)}}, {"_id": 1}).to_list(length=10000)
    result = await db.ingestJobs.delete_many({"status": {"$in": list(ingest_jobs.TERMINAL)}})
    for job in finished:
        cleanup_job(job["_id"])
    return {"removed": result.deleted_count}


@router.post("/upload")
async def upload_mp3s(
    files: list[UploadFile] = File(...), artist: str = Form(""), album: str = Form(""),
    year: str = Form(""), cover: UploadFile | None = File(None),
    db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin),
) -> dict:
    if not files or len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"Choose 1–{MAX_UPLOAD_FILES} MP3 files")
    with tempfile.TemporaryDirectory(prefix="upload-", dir=get_settings().ingest_path) as temp:
        staged: list[tuple[Path, dict]] = []
        for index, upload in enumerate(files, 1):
            if not (upload.filename or "").lower().endswith(".mp3"):
                raise HTTPException(status_code=400, detail="Only MP3 files are supported")
            path = Path(temp) / f"{index:02d}.mp3"
            await _save_upload(upload, path, MAX_UPLOAD_BYTES)
            staged.append((path, await asyncio.to_thread(read_tags, path)))
        cover_data = None
        if cover and cover.filename:
            data = await cover.read(MAX_COVER_BYTES + 1)
            if len(data) > MAX_COVER_BYTES:
                raise HTTPException(status_code=413, detail="Cover exceeds 8 MiB")
            cover_data = _validate_cover(data)
        resolved_artist = artist.strip() or staged[0][1]["artist"] or "Unknown Artist"
        resolved_album = album.strip() or staged[0][1]["album"] or "Unknown Album"
        resolved_year = year.strip() or staged[0][1]["year"]
        await asyncio.to_thread(
            promote_tracks,
            [(path, tags["title"] or Path(upload.filename or "").stem) for (path, tags), upload in zip(staged, files)],
            artist=resolved_artist, album=resolved_album, year=resolved_year, cover=cover_data,
        )
    scan_error = None
    try:
        await scan_jobs.enqueue_scan(db, triggered_by="ingest:upload")
    except Exception as exc:
        scan_error = str(exc)[:500]
    return {"ok": True, "count": len(staged), "artist": resolved_artist, "album": resolved_album, "scanError": scan_error}
