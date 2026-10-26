from __future__ import annotations

import html
import re
import unicodedata

PENALTIES = (
    "cover",
    "karaoke",
    "reaction",
    "sped up",
    "slowed",
    "8d",
    "nightcore",
    "compilation",
)


def normalize(value: str) -> str:
    value = html.unescape(unicodedata.normalize("NFKD", value)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def score_candidate(track: dict, candidate: dict) -> float:
    title = normalize(track["title"])
    artist = normalize(track["artist"])
    haystack = normalize(
        f"{candidate.get('title', '')} {candidate.get('channelTitle', '')}"
    )
    score = 0.0
    if title and title in haystack:
        score += 0.48
    else:
        title_words = set(title.split())
        score += (
            0.38 * len(title_words & set(haystack.split())) / max(1, len(title_words))
        )
    if artist and artist in haystack:
        score += 0.28
    if "official" in haystack or " topic" in f" {haystack}":
        score += 0.1
    expected = (track.get("durationMs") or 0) / 1000
    actual = candidate.get("durationSeconds") or 0
    if expected and actual:
        difference = abs(expected - actual)
        score += 0.14 if difference <= 10 else 0.07 if difference <= 20 else 0
    if any(term in haystack for term in PENALTIES):
        score -= 0.35
    if " live" in f" {haystack}" and " live" not in f" {normalize(track['title'])}":
        score -= 0.2
    if " remix" in f" {haystack}" and " remix" not in f" {normalize(track['title'])}":
        score -= 0.2
    return max(0.0, min(1.0, score))


def rank_candidates(
    track: dict, candidates: list[dict]
) -> tuple[list[dict], dict | None, str]:
    ranked = sorted(
        (
            {**candidate, "score": round(score_candidate(track, candidate), 3)}
            for candidate in candidates
        ),
        key=lambda item: item["score"],
        reverse=True,
    )
    if not ranked or ranked[0]["score"] < 0.55:
        return ranked, None, "unmatched"
    confidence = (
        "high"
        if ranked[0]["score"] >= 0.82
        else "medium"
        if ranked[0]["score"] >= 0.68
        else "low"
    )
    return ranked, ranked[0], confidence
