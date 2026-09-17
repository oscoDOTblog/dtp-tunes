"""Tests for playlist ordering helpers."""

from app.repositories.playlists import is_reorder_of


def test_accepts_only_an_exact_reordering():
    current = ["a", "b", "c"]
    assert is_reorder_of(current, ["c", "a", "b"])
    assert not is_reorder_of(current, ["a", "b"])
    assert not is_reorder_of(current, ["a", "b", "other"])


def test_reordering_preserves_duplicate_entries():
    current = ["a", "a", "b"]
    assert is_reorder_of(current, ["a", "b", "a"])
    assert not is_reorder_of(current, ["a", "b", "b"])
