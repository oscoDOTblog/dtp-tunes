"""Pydantic schemas shared by the API routes, repositories, and worker.

MongoDB documents use plain camelCase dicts (see app/repositories); these
models describe request/response payloads and give repositories a typed
shape to build documents from.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserOut(CamelModel):
    id: str
    username: str
    role: Role
    isActive: bool
    createdAt: datetime


class UserCreate(CamelModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    role: Role = Role.USER


class LoginRequest(CamelModel):
    username: str
    password: str


class ApiKeyOut(CamelModel):
    id: str
    keyId: str
    name: str
    createdAt: datetime
    lastUsedAt: datetime | None = None
    revokedAt: datetime | None = None


class ApiKeyCreated(ApiKeyOut):
    fullKey: str


class ApiKeyCreate(CamelModel):
    name: str = Field(min_length=1, max_length=128)


class ArtistOut(CamelModel):
    id: str
    name: str
    sortName: str
    albumCount: int
    coverArtId: str | None = None


class AlbumOut(CamelModel):
    id: str
    name: str
    artistId: str | None
    artistName: str | None
    year: int | None = None
    genre: str | None = None
    songCount: int
    duration: int
    coverArtId: str | None = None
    createdAt: datetime


class SongOut(CamelModel):
    id: str
    title: str
    albumId: str | None
    albumName: str | None
    artistId: str | None
    artistName: str | None
    genre: str | None = None
    track: int | None = None
    discNumber: int | None = None
    year: int | None = None
    duration: int
    bitrate: int | None = None
    suffix: str
    contentType: str
    size: int
    coverArtId: str | None = None
    starred: bool = False
    playCount: int = 0


class GenreOut(CamelModel):
    name: str
    songCount: int
    albumCount: int


class PlaylistOut(CamelModel):
    id: str
    ownerId: str
    name: str
    comment: str | None = None
    public: bool
    songCount: int
    duration: int
    createdAt: datetime
    updatedAt: datetime
    coverArtIds: list[str] = Field(default_factory=list)
    containsSong: bool | None = None


class PlaylistCreate(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    comment: str | None = None
    public: bool = False
    songIds: list[str] = Field(default_factory=list)


class PlaylistUpdate(CamelModel):
    name: str | None = None
    comment: str | None = None
    public: bool | None = None
    songIdsToAdd: list[str] = Field(default_factory=list)
    songIndexesToRemove: list[int] = Field(default_factory=list)


class StarTargetType(str, Enum):
    SONG = "song"
    ALBUM = "album"
    ARTIST = "artist"


class PlayQueueOut(CamelModel):
    current: str | None
    position: int
    songIds: list[str]
    changedAt: datetime | None = None


class PlayQueueSave(CamelModel):
    current: str | None = None
    position: int = 0
    songIds: list[str] = Field(default_factory=list)


class ScanJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanJobOut(CamelModel):
    id: str
    status: ScanJobStatus
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
    scannedCount: int = 0
    addedCount: int = 0
    updatedCount: int = 0
    removedCount: int = 0
    errorCount: int = 0
    lastError: str | None = None


class SearchResult(CamelModel):
    artists: list[ArtistOut]
    albums: list[AlbumOut]
    songs: list[SongOut]


class HealthOut(CamelModel):
    status: Literal["ok", "degraded"]
    mongodb: bool
    version: str


class LibraryResetOut(CamelModel):
    songs: int = 0
    albums: int = 0
    artists: int = 0
    genres: int = 0
    stars: int = 0
    playHistory: int = 0
    playQueues: int = 0
    scanJobs: int = 0
    playlistsCleared: int = 0
    coversCleared: int = 0
    rescanEnqueued: bool = False
    scanJob: ScanJobOut | None = None
