"""Persist extracted cover art into the writable cache volume."""

from __future__ import annotations

import io
import logging
import os
import shutil

from PIL import Image

from app.config import get_settings

logger = logging.getLogger("dtp_tunes.worker.artwork")

MAX_DIMENSION = 1000


def save_album_cover(album_id: str, raw_bytes: bytes) -> str | None:
    """Saves a resized JPEG under CACHE_PATH/covers/{albumId}.jpg. Returns the relative path."""
    settings = get_settings()
    covers_dir = os.path.join(settings.cache_path, "covers")
    os.makedirs(covers_dir, exist_ok=True)
    relative_path = os.path.join("covers", f"{album_id}.jpg")
    absolute_path = os.path.join(settings.cache_path, relative_path)

    try:
        image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        image.save(absolute_path, format="JPEG", quality=88)
        return relative_path
    except Exception:  # noqa: BLE001
        logger.warning("Failed to save cover art for album %s", album_id, exc_info=True)
        return None


def clear_cover_cache() -> int:
    """Remove all cached cover JPEGs. Returns the number of files deleted."""
    settings = get_settings()
    covers_dir = os.path.join(settings.cache_path, "covers")
    if not os.path.isdir(covers_dir):
        return 0
    deleted = 0
    for name in os.listdir(covers_dir):
        path = os.path.join(covers_dir, name)
        try:
            if os.path.isfile(path):
                os.remove(path)
                deleted += 1
            elif os.path.isdir(path):
                shutil.rmtree(path)
                deleted += 1
        except OSError:
            logger.warning("Failed to remove cover cache entry %s", path, exc_info=True)
    return deleted
