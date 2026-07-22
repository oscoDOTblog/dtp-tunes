"""Worker process entrypoint: leases and runs scan jobs on a periodic interval.

Run separately from the API process (`python -m app.worker.main`) so that
streaming stays responsive while the scanner walks the filesystem.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket

from app.config import get_settings
from app.db import close_connection, ensure_indexes, get_database
from app.repositories import scan_jobs as scan_jobs_repo
from app.worker.scanner import run_scan_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dtp_tunes.worker")

_OWNER = f"{socket.gethostname()}-{os.getpid()}"


async def _worker_loop() -> None:
    settings = get_settings()
    db = get_database()
    await ensure_indexes()

    # Seed an initial scan on first boot so the library isn't empty until the next interval.
    latest = await scan_jobs_repo.latest_job(db)
    if latest is None:
        await scan_jobs_repo.enqueue_scan(db, triggered_by="startup")

    last_periodic_enqueue = 0.0
    loop = asyncio.get_event_loop()

    logger.info("Worker started (owner=%s, interval=%ss)", _OWNER, settings.scan_interval_seconds)

    while True:
        job = await scan_jobs_repo.try_lease_next_job(db, owner=_OWNER)
        if job:
            logger.info("Leased scan job %s", job["_id"])
            try:
                await run_scan_job(db, job["_id"], owner=_OWNER)
            except Exception:  # noqa: BLE001
                logger.exception("Scan job %s crashed", job["_id"])
                await scan_jobs_repo.complete_job(db, job["_id"], status="failed", last_error="worker crashed")
        else:
            now = loop.time()
            if now - last_periodic_enqueue > settings.scan_interval_seconds:
                await scan_jobs_repo.enqueue_scan(db, triggered_by="scheduler")
                last_periodic_enqueue = now
            await asyncio.sleep(5)


async def main() -> None:
    try:
        await _worker_loop()
    finally:
        await close_connection()


if __name__ == "__main__":
    asyncio.run(main())
