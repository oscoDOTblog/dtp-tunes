"use client";

import { useEffect, useRef } from "react";
import { usePlayerStore } from "@/store/playerStore";
import { api, coverUrl, streamUrl } from "@/lib/api";
import { registerAudioElement } from "@/lib/audioController";

/**
 * Owns the single HTMLAudioElement for the whole app and keeps it in sync
 * with the Zustand player store. Mounted once near the root layout.
 * Uses a native <audio> element (not a player library) to preserve
 * range-request seeking and full Media Session control.
 */
export function AudioEngine() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastLoadedSongId = useRef<string | null>(null);

  const isPlaying = usePlayerStore((s) => s.isPlaying);
  const volume = usePlayerStore((s) => s.volume);
  const muted = usePlayerStore((s) => s.muted);
  const currentIndex = usePlayerStore((s) => s.currentIndex);
  const queue = usePlayerStore((s) => s.queue);
  const currentSong = usePlayerStore((s) => s.currentSong());
  const setCurrentTime = usePlayerStore((s) => s.setCurrentTime);
  const setDuration = usePlayerStore((s) => s.setDuration);
  const setLoading = usePlayerStore((s) => s.setLoading);
  const handleEnded = usePlayerStore((s) => s.handleEnded);
  const next = usePlayerStore((s) => s.next);
  const previous = usePlayerStore((s) => s.previous);
  const play = usePlayerStore((s) => s.play);
  const pause = usePlayerStore((s) => s.pause);

  useEffect(() => {
    audioRef.current = new Audio();
    audioRef.current.preload = "metadata";
    registerAudioElement(audioRef.current);
    const audio = audioRef.current;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => {
      setDuration(audio.duration || 0);
      setLoading(false);
    };
    const onWaiting = () => setLoading(true);
    const onPlaying = () => setLoading(false);
    const onEnded = () => handleEnded();

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("loadedmetadata", onLoadedMetadata);
    audio.addEventListener("waiting", onWaiting);
    audio.addEventListener("playing", onPlaying);
    audio.addEventListener("ended", onEnded);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("loadedmetadata", onLoadedMetadata);
      audio.removeEventListener("waiting", onWaiting);
      audio.removeEventListener("playing", onPlaying);
      audio.removeEventListener("ended", onEnded);
      audio.pause();
      registerAudioElement(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !currentSong) return;
    if (lastLoadedSongId.current === currentSong.id) return;
    lastLoadedSongId.current = currentSong.id;
    setLoading(true);
    audio.src = streamUrl(currentSong.id);
    audio.load();
    if (isPlaying) {
      audio.play().catch(() => undefined);
    }
    api.post(`/api/songs/${currentSong.id}/scrobble`).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSong?.id]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) audio.play().catch(() => undefined);
    else audio.pause();
  }, [isPlaying]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = muted ? 0 : volume;
  }, [volume, muted]);

  // Sync queue/current position to the server so it survives reloads/devices.
  useEffect(() => {
    if (!currentSong) return;
    const timeout = setTimeout(() => {
      api
        .put("/api/queue", {
          current: currentSong.id,
          position: currentIndex,
          songIds: queue.map((s) => s.id),
        })
        .catch(() => undefined);
    }, 1500);
    return () => clearTimeout(timeout);
  }, [currentSong, currentIndex, queue]);

  useEffect(() => {
    if (typeof window === "undefined" || !("mediaSession" in navigator) || !currentSong) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: currentSong.title,
      artist: currentSong.artistName ?? undefined,
      album: currentSong.albumName ?? undefined,
      artwork: currentSong.coverArtId
        ? [{ src: coverUrl(currentSong.coverArtId, 512), sizes: "512x512", type: "image/jpeg" }]
        : [],
    });
    navigator.mediaSession.setActionHandler("play", () => play());
    navigator.mediaSession.setActionHandler("pause", () => pause());
    navigator.mediaSession.setActionHandler("nexttrack", () => next());
    navigator.mediaSession.setActionHandler("previoustrack", () => previous());
    navigator.mediaSession.setActionHandler("seekto", (details) => {
      if (audioRef.current && details.seekTime != null) {
        audioRef.current.currentTime = details.seekTime;
      }
    });
  }, [currentSong, play, pause, next, previous]);

  useEffect(() => {
    if (typeof window === "undefined" || !("mediaSession" in navigator)) return;
    navigator.mediaSession.playbackState = isPlaying ? "playing" : "paused";
  }, [isPlaying]);

  return null;
}
