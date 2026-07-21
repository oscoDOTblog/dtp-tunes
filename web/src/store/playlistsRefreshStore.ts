import { create } from "zustand";

/**
 * Cross-component playlist refresh signal. Any component that mutates
 * playlists calls bump(); components that display playlist lists include
 * `version` in their fetch dependencies so they refetch automatically.
 */
interface PlaylistsRefreshState {
  version: number;
  bump: () => void;
}

export const usePlaylistsRefresh = create<PlaylistsRefreshState>((set) => ({
  version: 0,
  bump: () => set((state) => ({ version: state.version + 1 })),
}));
