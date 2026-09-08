"""Smoke test that the download endpoints are registered (FastAPI >=0.139 keeps
included routers lazy, so assert on the router plus its inclusion in the app)."""

from __future__ import annotations

from app.main import app
from app.routes import api_library, api_media


def _router_paths(router) -> set[str]:
    return {route.path for route in router.routes if hasattr(route, "path")}


def _included_routers() -> list:
    return [route for route in app.routes if type(route).__name__ == "_IncludedRouter"]


def test_download_routes_defined():
    paths = _router_paths(api_media.router)
    assert "/api/download/{song_id}" in paths
    assert "/api/albums/{album_id}/download" in paths
    # Playback + browse routes still mounted alongside the new ones.
    assert "/api/stream/{song_id}" in paths
    assert "/api/albums/{album_id}" in _router_paths(api_library.router)


def test_media_router_included_in_app():
    assert any(route.original_router is api_media.router for route in _included_routers())
