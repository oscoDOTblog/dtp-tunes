from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "dtp-tunes"
    app_public_url: str = "http://localhost:8080"
    admin_username: str = "admin"
    admin_password: str = Field(default="changeme-admin-password", min_length=8)
    app_encryption_key: str = Field(min_length=32)

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "DTP"
    mongodb_collection_prefix: str = "tunes_"

    music_path: str = "/music"
    cache_path: str = "/cache"
    music_folder_name: str = "Music"
    music_folder_id: str = "1"

    scan_interval_seconds: int = 300
    ffmpeg_max_concurrent: int = 2
    # How long a transcode request waits for a free FFmpeg slot before the
    # server fails fast with 503 (so clients show an error instead of
    # hanging forever on an unanswered request).
    ffmpeg_queue_timeout_seconds: int = 30

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:8080,http://localhost:3000"

    session_cookie_name: str = "dtp_tunes_session"
    session_ttl_seconds: int = 604800

    @field_validator("app_encryption_key")
    @classmethod
    def encryption_key_strength(cls, value: str) -> str:
        if len(value.encode("utf-8")) < 32:
            raise ValueError("APP_ENCRYPTION_KEY must be at least 32 bytes")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
