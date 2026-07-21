"""Resolve and resize cached cover art images for getCoverArt / /api/covers."""

from __future__ import annotations

import io
import os

from fastapi import HTTPException
from fastapi.responses import Response
from PIL import Image

from app.config import get_settings

_PLACEHOLDER_SIZE = (300, 300)


def resolve_cache_path(relative_path: str) -> str | None:
    settings = get_settings()
    base = os.path.realpath(settings.cache_path)
    candidate = os.path.realpath(os.path.join(base, relative_path))
    if not (candidate == base or candidate.startswith(base + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.isfile(candidate):
        return None
    return candidate


def render_cover_art(cover_art_path: str | None, *, size: int | None = None) -> Response:
    if cover_art_path:
        absolute = resolve_cache_path(cover_art_path)
    else:
        absolute = None

    if absolute is None:
        image = Image.new("RGB", _PLACEHOLDER_SIZE, color=(30, 30, 30))
    else:
        image = Image.open(absolute).convert("RGB")

    if size:
        image.thumbnail((size, size))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return Response(content=buffer.getvalue(), media_type="image/jpeg")
