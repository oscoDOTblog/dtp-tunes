"use client";

import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { detailedSongColumns, SongRow } from "@/components/music/SongRow";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/ToastProvider";
import { api } from "@/lib/api";
import type { Song } from "@/lib/types";
import { useFetch } from "@/lib/useFetch";
import { cn } from "@/lib/utils";

const columns = [
  { key: "title", label: "Song" },
  { key: "albumName", label: "Album" },
  { key: "artistName", label: "Artist" },
  { key: "year", label: "Year" },
] as const;

type SortKey = (typeof columns)[number]["key"];
const pageSize = 50;

export function LibrarySongs() {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; descending: boolean }>({ key: "title", descending: false });
  const [page, setPage] = useState(0);

  useEffect(() => {
    const nextQuery = search.trim();
    if (nextQuery === query) return;
    const timeout = window.setTimeout(() => {
      setQuery(nextQuery);
      setPage(0);
    }, nextQuery ? 250 : 0);
    return () => window.clearTimeout(timeout);
  }, [search, query]);

  function changeSort(key: SortKey) {
    setSort((current) => ({ key, descending: current.key === key && !current.descending }));
    setPage(0);
  }

  const direction = sort.descending ? "Descending" : "Ascending";
  const SortArrow = sort.descending ? ArrowDown : ArrowUp;
  const params = new URLSearchParams({
    q: query,
    sort: sort.key,
    direction: sort.descending ? "desc" : "asc",
    skip: String(page * pageSize),
    limit: String(pageSize),
  });

  return (
    <div className="flex flex-col gap-4">
      <Input
        type="search"
        aria-label="Filter songs"
        placeholder="Search songs, albums, artists, or years"
        value={search}
        maxLength={300}
        onChange={(event) => setSearch(event.target.value)}
        className="max-w-md"
      />
      <div className="flex flex-wrap items-center gap-2 md:hidden">
        <label htmlFor="song-sort" className="text-sm text-fg-secondary">Sort by</label>
        <select
          id="song-sort"
          className="h-8 rounded-lg border border-border-subtle bg-bg-elevated-2 px-2 text-sm text-fg-primary"
          value={sort.key}
          onChange={(event) => changeSort(event.target.value as SortKey)}
        >
          {columns.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
        </select>
        <Button size="sm" variant="outline" onClick={() => changeSort(sort.key)}>
          <SortArrow size={14} aria-hidden="true" />
          {direction}
        </Button>
      </div>

      <div className={cn("hidden items-center gap-4 border-b border-border-subtle px-3 pb-2 text-sm text-fg-secondary md:grid", detailedSongColumns)}>
        <span />
        {columns.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={cn("flex w-fit items-center gap-1 text-left hover:text-fg-primary", sort.key === key && "text-fg-primary")}
            aria-label={sort.key === key ? `${label}, sorted ${direction.toLowerCase()}` : `Sort by ${label}`}
            onClick={() => changeSort(key)}
          >
            {label}
            {sort.key === key && <SortArrow size={14} aria-hidden="true" />}
          </button>
        ))}
        <span />
        <span>Time</span>
      </div>
      <SongResults key={params.toString()} path={`/api/songs?${params}`} query={query} page={page} setPage={setPage} />
    </div>
  );
}

function SongResults({ path, query, page, setPage }: {
  path: string;
  query: string;
  page: number;
  setPage: (page: number) => void;
}) {
  const { data, isLoading, error, refetch } = useFetch<{ songs: Song[]; hasMore: boolean }>(path);
  const toast = useToast();

  async function toggleStar(song: Song) {
    try {
      const url = `/api/songs/${encodeURIComponent(song.id)}/star`;
      if (song.starred) await api.delete(url);
      else await api.post(url);
      refetch();
    } catch {
      toast.error("Could not update liked songs");
    }
  }

  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (!data && isLoading) return <p role="status" className="text-sm text-fg-secondary">Loading songs…</p>;
  if (!data) return null;

  return (
    <>
      {data.songs.length === 0 && (
        <EmptyState
          title={query ? "No matching songs" : "No songs found"}
          description={query ? "Try a different search." : undefined}
        />
      )}
      <div className="flex flex-col">
        {data.songs.map((song, index) => (
          <SongRow
            key={song.id}
            song={song}
            index={index}
            queue={data.songs}
            showCover
            showDetails
            onToggleStar={toggleStar}
            onDeleted={() => {
              if (page > 0 && data.songs.length === 1) setPage(page - 1);
              else refetch();
            }}
          />
        ))}
      </div>
      {(page > 0 || data.hasMore) && (
        <nav aria-label="Song pages" className="flex items-center justify-center gap-3">
          <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
          <span className="text-sm text-fg-secondary">Page {page + 1}</span>
          <Button size="sm" variant="outline" disabled={!data.hasMore} onClick={() => setPage(page + 1)}>Next</Button>
        </nav>
      )}
    </>
  );
}
