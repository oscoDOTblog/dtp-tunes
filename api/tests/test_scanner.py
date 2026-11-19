from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.repositories import catalog
from app.worker import scanner


@pytest.mark.asyncio
async def test_empty_mount_preserves_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner, "get_settings", lambda: SimpleNamespace(music_path=str(tmp_path)))
    monkeypatch.setattr(catalog, "all_song_paths", AsyncMock(return_value={"song.flac"}))
    remove_songs = AsyncMock()
    monkeypatch.setattr(catalog, "delete_songs_by_paths", remove_songs)
    complete_job = AsyncMock()
    monkeypatch.setattr(scanner.scan_jobs_repo, "complete_job", complete_job)
    db = Mock()

    await scanner.run_scan_job(db, "scan", owner="worker")

    remove_songs.assert_not_awaited()
    assert complete_job.await_args.kwargs["status"] == "failed"
    assert "mount" in complete_job.await_args.kwargs["last_error"]


@pytest.mark.asyncio
async def test_returning_song_reuses_saved_id():
    song = {"_id": "playlist-song-id", "path": "album/song.flac"}
    songs = Mock()
    songs.find.return_value.to_list = AsyncMock(return_value=[song])
    songs.delete_many = AsyncMock()
    songs.find_one = AsyncMock(return_value=None)
    songs.insert_one = AsyncMock()
    missing_ids = Mock()
    missing_ids.bulk_write = AsyncMock()
    missing_ids.find_one = AsyncMock(return_value={"_id": song["path"], "songId": song["_id"]})
    db = SimpleNamespace(songs=songs, missingSongIds=missing_ids)

    await catalog.delete_songs_by_paths(db, [song["path"]])
    operations = missing_ids.bulk_write.await_args.args[0]
    assert operations == [
        catalog.UpdateOne({"_id": song["path"]}, {"$set": {"songId": song["_id"]}}, upsert=True)
    ]
    songs.delete_many.assert_awaited_once_with({"_id": {"$in": [song["_id"]]}})

    restored, created = await catalog.upsert_song_by_path(db, path=song["path"], fields={})

    assert created
    assert restored["_id"] == song["_id"]
    songs.insert_one.assert_awaited_once_with(restored)
