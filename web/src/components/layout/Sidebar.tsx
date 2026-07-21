"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Search, Library, ListMusic, Settings, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFetch } from "@/lib/useFetch";
import { PlaylistListItem } from "@/components/music/PlaylistListItem";
import { api } from "@/lib/api";
import type { Playlist } from "@/lib/types";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/search", label: "Search", icon: Search },
  { href: "/library", label: "Your Library", icon: Library },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: playlists, refetch } = useFetch<Playlist[]>("/api/playlists");

  async function createPlaylist() {
    await api.post("/api/playlists", { name: "New Playlist", songIds: [] });
    refetch();
  }

  return (
    <aside className="hidden h-full w-64 flex-shrink-0 flex-col gap-2 border-r border-border-subtle bg-bg-base p-3 md:flex">
      <div className="mb-2 flex items-center gap-2 px-3 py-3">
        <span className="text-xl font-bold tracking-tight text-accent">dtp-tunes</span>
      </div>

      <nav className="flex flex-col gap-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-bg-elevated-2 text-fg-primary" : "text-fg-secondary hover:text-fg-primary hover:bg-bg-hover"
              )}
            >
              <Icon size={20} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-4 flex items-center justify-between px-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-fg-secondary">
          <ListMusic size={16} />
          Playlists
        </span>
        <button onClick={createPlaylist} className="text-fg-secondary hover:text-fg-primary" aria-label="Create playlist">
          <Plus size={16} />
        </button>
      </div>

      <div className="scrollbar-none flex-1 overflow-y-auto px-1">
        {(playlists ?? []).map((playlist) => (
          <PlaylistListItem key={playlist.id} playlist={playlist} active={pathname === `/playlist/${playlist.id}`} />
        ))}
      </div>

      <Link
        href="/settings"
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          pathname === "/settings" ? "bg-bg-elevated-2 text-fg-primary" : "text-fg-secondary hover:text-fg-primary hover:bg-bg-hover"
        )}
      >
        <Settings size={20} />
        Settings
      </Link>
    </aside>
  );
}
