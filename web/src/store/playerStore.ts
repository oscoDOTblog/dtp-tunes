"use client";

import { create } from "zustand";
import type { Song } from "@/lib/types";

export type RepeatMode = "off" | "all" | "one";

interface PlayerState {
  queue: Song[];
  currentIndex: number;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  muted: boolean;
  shuffle: boolean;
  repeat: RepeatMode;
  isLoading: boolean;

  currentSong: () => Song | null;

  playQueue: (songs: Song[], startIndex?: number) => void;
  addToQueue: (song: Song) => void;
  playNext: (song: Song) => void;
  removeFromQueue: (index: number) => void;
  clearQueue: () => void;

  togglePlay: () => void;
  play: () => void;
  pause: () => void;
  next: () => void;
  previous: () => void;
  jumpTo: (index: number) => void;

  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  toggleShuffle: () => void;
  cycleRepeat: () => void;
  setLoading: (loading: boolean) => void;
  handleEnded: () => void;
}

function shuffleIndexOrder(length: number, exclude: number): number[] {
  const indexes = Array.from({ length }, (_, i) => i).filter((i) => i !== exclude);
  for (let i = indexes.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [indexes[i], indexes[j]] = [indexes[j], indexes[i]];
  }
  return indexes;
}

export const usePlayerStore = create<PlayerState>((set, get) => ({
  queue: [],
  currentIndex: -1,
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 1,
  muted: false,
  shuffle: false,
  repeat: "off",
  isLoading: false,

  currentSong: () => {
    const { queue, currentIndex } = get();
    return currentIndex >= 0 && currentIndex < queue.length ? queue[currentIndex] : null;
  },

  playQueue: (songs, startIndex = 0) => {
    set({ queue: songs, currentIndex: startIndex, isPlaying: songs.length > 0, currentTime: 0 });
  },

  addToQueue: (song) => {
    set((state) => ({ queue: [...state.queue, song] }));
  },

  playNext: (song) => {
    set((state) => {
      const insertAt = state.currentIndex + 1;
      const queue = [...state.queue.slice(0, insertAt), song, ...state.queue.slice(insertAt)];
      return { queue };
    });
  },

  removeFromQueue: (index) => {
    set((state) => {
      const queue = state.queue.filter((_, i) => i !== index);
      let currentIndex = state.currentIndex;
      if (index < currentIndex) currentIndex -= 1;
      else if (index === currentIndex) currentIndex = Math.min(currentIndex, queue.length - 1);
      return { queue, currentIndex };
    });
  },

  clearQueue: () => set({ queue: [], currentIndex: -1, isPlaying: false }),

  togglePlay: () => set((state) => ({ isPlaying: state.queue.length > 0 && !state.isPlaying })),
  play: () => set((state) => ({ isPlaying: state.queue.length > 0 ? true : state.isPlaying })),
  pause: () => set({ isPlaying: false }),

  next: () => {
    const { queue, currentIndex, shuffle, repeat } = get();
    if (queue.length === 0) return;
    if (shuffle) {
      const order = shuffleIndexOrder(queue.length, currentIndex);
      if (order.length === 0) {
        if (repeat === "all") set({ currentIndex: currentIndex, currentTime: 0 });
        else set({ isPlaying: false });
        return;
      }
      set({ currentIndex: order[0], currentTime: 0, isPlaying: true });
      return;
    }
    const nextIndex = currentIndex + 1;
    if (nextIndex < queue.length) {
      set({ currentIndex: nextIndex, currentTime: 0, isPlaying: true });
    } else if (repeat === "all") {
      set({ currentIndex: 0, currentTime: 0, isPlaying: true });
    } else {
      set({ isPlaying: false });
    }
  },

  previous: () => {
    const { queue, currentIndex, currentTime } = get();
    if (queue.length === 0) return;
    if (currentTime > 3) {
      set({ currentTime: 0 });
      return;
    }
    const prevIndex = currentIndex - 1;
    if (prevIndex >= 0) {
      set({ currentIndex: prevIndex, currentTime: 0, isPlaying: true });
    } else {
      set({ currentTime: 0 });
    }
  },

  jumpTo: (index) => {
    const { queue } = get();
    if (index >= 0 && index < queue.length) {
      set({ currentIndex: index, currentTime: 0, isPlaying: true });
    }
  },

  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setVolume: (volume) => set({ volume, muted: volume === 0 }),
  toggleMute: () => set((state) => ({ muted: !state.muted })),
  toggleShuffle: () => set((state) => ({ shuffle: !state.shuffle })),
  cycleRepeat: () =>
    set((state) => ({
      repeat: state.repeat === "off" ? "all" : state.repeat === "all" ? "one" : "off",
    })),
  setLoading: (loading) => set({ isLoading: loading }),

  handleEnded: () => {
    const { repeat } = get();
    if (repeat === "one") {
      set({ currentTime: 0, isPlaying: true });
      return;
    }
    get().next();
  },
}));
