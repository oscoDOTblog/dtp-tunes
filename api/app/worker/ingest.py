"""Isolated yt-dlp worker with MongoDB leases and cooperative cancellation."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from pathlib import Path

from app.config import get_settings
from app.db import close_connection, ensure_indexes, get_database
from app.repositories import ingest_jobs, scan_jobs
from app.repositories.base import utcnow
from app.services.ingest import cleanup_job, job_dir, promote_tracks

logger = logging.getLogger("dtp_tunes.ingest")


async def _download(db, job: dict, owner: str) -> list[dict]:
    target = job_dir(job["_id"])
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob("*.mp3"):
        old.unlink()
    args = [
        "yt-dlp", "--yes-playlist",
        "--extract-audio", "--audio-format", "mp3", "--newline",
        "--write-thumbnail", "--convert-thumbnails", "jpg",
        "-f", "bestaudio/best", "-o", str(target / "%(playlist_index)02d - %(title)s.%(ext)s"),
        job["url"],
    ]
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    output: list[str] = []
    try:
        while process.returncode is None:
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=2)
            except asyncio.TimeoutError:
                line = b""
            if line:
                message = line.decode("utf-8", errors="replace").strip()
                output.append(message)
                output = output[-30:]
                if message.startswith("[download] Destination:"):
                    await ingest_jobs.progress(db, job["_id"], owner, currentTitle=Path(message.split(":", 1)[1].strip()).stem)
            current = await ingest_jobs.get(db, job["_id"])
            if not current or current.get("cancelRequested") or current.get("leaseOwner") != owner:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                raise asyncio.CancelledError
            await ingest_jobs.progress(db, job["_id"], owner)
            if not line and process.returncode is None:
                await asyncio.sleep(0.1)
            if process.stdout.at_eof():
                break
        code = await process.wait()
        if code:
            raise RuntimeError("yt-dlp failed: " + "\n".join(output[-8:])[-1500:])
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    files = sorted(target.glob("*.mp3"))
    if not files:
        raise RuntimeError("yt-dlp produced no MP3 files")
    if not job.get("coverName"):
        thumbnails = sorted(target.glob("*.jpg"))
        if thumbnails:
            (target / "source.jpg").write_bytes(thumbnails[0].read_bytes())
    return [{"id": index, "filename": file.name, "title": file.stem.split(" - ", 1)[-1]} for index, file in enumerate(files, 1)]


async def _process(db, job: dict, owner: str) -> None:
    job_id = job["_id"]
    try:
        tracks = await _download(db, job, owner)
        if job["mode"] == "oneOff":
            await ingest_jobs.finish(db, job_id, owner, status="readyForReview", tracks=tracks, current=len(tracks), total=len(tracks))
            return
        current = await ingest_jobs.get(db, job_id)
        if not current or current.get("cancelRequested"):
            raise asyncio.CancelledError
        staging = job_dir(job_id)
        cover_path = staging / (job.get("coverName") or "source.jpg")
        cover = cover_path.read_bytes() if cover_path.is_file() else None
        promotion = asyncio.create_task(asyncio.to_thread(
            promote_tracks,
            [(staging / track["filename"], track["title"]) for track in tracks],
            artist=job["album"].get("artist") or "Unknown Artist",
            album=job["album"].get("title") or "Unknown Album",
            year=job["album"].get("year") or "", cover=cover,
        ))
        while not promotion.done():
            await ingest_jobs.progress(db, job_id, owner)
            await asyncio.wait({promotion}, timeout=15)
        await promotion
        scan_error = None
        try:
            await scan_jobs.enqueue_scan(db, triggered_by=f"ingest:{job_id}")
        except Exception as exc:
            scan_error = str(exc)[:500]
        finished = await ingest_jobs.finish(
            db, job_id, owner, status="completed", tracks=[], current=len(tracks), total=len(tracks),
            finishedAt=utcnow(), scanError=scan_error,
        )
        if finished:
            cleanup_job(job_id)
    except asyncio.CancelledError:
        await ingest_jobs.update(db, job_id, status="cancelled", finishedAt=utcnow(), leaseOwner=None, leaseExpiresAt=None)
        cleanup_job(job_id)
    except Exception as exc:
        logger.exception("Ingest job %s failed", job_id)
        await ingest_jobs.update(db, job_id, status="failed", error=str(exc)[:1500], finishedAt=utcnow(), leaseOwner=None, leaseExpiresAt=None)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await ensure_indexes()
    db = get_database()
    owner = f"{socket.gethostname()}-{os.getpid()}"
    workers = max(1, get_settings().ingest_workers)
    async def loop(index: int) -> None:
        worker_owner = f"{owner}-{index}"
        while True:
            job = await ingest_jobs.lease(db, worker_owner)
            if job:
                await _process(db, job, worker_owner)
            else:
                await asyncio.sleep(2)
    try:
        await asyncio.gather(*(loop(index) for index in range(workers)))
    finally:
        await close_connection()


if __name__ == "__main__":
    asyncio.run(main())
