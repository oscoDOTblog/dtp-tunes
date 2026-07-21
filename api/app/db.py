"""MongoDB connection pooling and index management (motor async client)."""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger("dtp_tunes.db")

_client: AsyncIOMotorClient | None = None
_db: PrefixedDatabase | None = None


class PrefixedDatabase:
    """Database facade that namespaces every collection with a prefix.

    dtp-tunes shares the `DTP` database with other apps, so `db.users`
    resolves to the `tunes_users` collection, `db.scanJobs` to
    `tunes_scanJobs`, etc. All repository code accesses collections via
    attribute (or item) lookup on this object, keeping the prefix in one
    place.
    """

    def __init__(self, database: AsyncIOMotorDatabase, prefix: str) -> None:
        self._database = database
        self._prefix = prefix

    def __getattr__(self, name: str) -> AsyncIOMotorCollection:
        return self._database[f"{self._prefix}{name}"]

    def __getitem__(self, name: str) -> AsyncIOMotorCollection:
        return self._database[f"{self._prefix}{name}"]


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_uri, uuidRepresentation="standard")
    return _client


def get_database() -> PrefixedDatabase:
    global _db
    if _db is None:
        settings = get_settings()
        _db = PrefixedDatabase(get_client()[settings.mongodb_db], settings.mongodb_collection_prefix)
    return _db


async def close_connection() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


async def ping() -> bool:
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("MongoDB ping failed")
        return False


async def ensure_indexes() -> None:
    """Create all collection indexes. Safe to call on every startup (idempotent)."""
    db = get_database()

    await db.users.create_index("normalizedUsername", unique=True)
    await db.users.create_index("role")

    await db.apiKeys.create_index("keyId", unique=True)
    await db.apiKeys.create_index("userId")

    await db.artists.create_index("normalizedName")
    await db.artists.create_index("sortName")

    await db.albums.create_index("artistId")
    await db.albums.create_index("normalizedName")
    await db.albums.create_index([("artistId", 1), ("normalizedName", 1)])

    await db.songs.create_index("path", unique=True)
    await db.songs.create_index("albumId")
    await db.songs.create_index("artistId")
    await db.songs.create_index("genre")
    await db.songs.create_index("normalizedTitle")

    await db.genres.create_index("name", unique=True)

    await db.playlists.create_index("ownerId")

    await db.stars.create_index([("userId", 1), ("itemId", 1), ("itemType", 1)], unique=True)
    await db.stars.create_index("userId")

    await db.playHistory.create_index([("userId", 1), ("playedAt", -1)])
    await db.playHistory.create_index("songId")

    await db.playQueues.create_index("userId", unique=True)

    await db.scanJobs.create_index("status")
    await db.scanJobs.create_index("leaseExpiresAt")

    await db.sessions.create_index("expiresAt", expireAfterSeconds=0)
    await db.sessions.create_index("userId")

    logger.info("MongoDB indexes ensured")
