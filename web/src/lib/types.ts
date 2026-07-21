export type Role = "admin" | "user";

export interface User {
  id: string;
  username: string;
  role: Role;
  isActive: boolean;
  createdAt: string;
}

export interface Artist {
  id: string;
  name: string;
  sortName: string;
  albumCount: number;
  coverArtId?: string | null;
}

export interface Album {
  id: string;
  name: string;
  artistId: string | null;
  artistName: string | null;
  year?: number | null;
  genre?: string | null;
  songCount: number;
  duration: number;
  coverArtId?: string | null;
  createdAt: string;
}

export interface Song {
  id: string;
  title: string;
  albumId: string | null;
  albumName: string | null;
  artistId: string | null;
  artistName: string | null;
  genre?: string | null;
  track?: number | null;
  discNumber?: number | null;
  year?: number | null;
  duration: number;
  bitrate?: number | null;
  suffix: string;
  contentType: string;
  size: number;
  coverArtId?: string | null;
  starred: boolean;
  playCount: number;
}

export interface Genre {
  name: string;
  songCount: number;
  albumCount: number;
}

export interface Playlist {
  id: string;
  ownerId: string;
  name: string;
  comment?: string | null;
  public: boolean;
  songCount: number;
  duration: number;
  createdAt: string;
  updatedAt: string;
  coverArtIds?: string[];
  containsSong?: boolean | null;
}

export interface SearchResult {
  artists: Artist[];
  albums: Album[];
  songs: Song[];
}

export interface ApiKey {
  id: string;
  keyId: string;
  name: string;
  createdAt: string;
  lastUsedAt?: string | null;
  revokedAt?: string | null;
}

export interface ScanJob {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  startedAt?: string | null;
  finishedAt?: string | null;
  scannedCount: number;
  addedCount: number;
  updatedCount: number;
  removedCount: number;
  errorCount: number;
  lastError?: string | null;
}
