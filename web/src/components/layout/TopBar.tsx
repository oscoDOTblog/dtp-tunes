"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Search, LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/useAuth";

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <header className="flex h-16 flex-shrink-0 items-center justify-between gap-4 border-b border-border-subtle bg-bg-base/80 px-4 backdrop-blur">
      <form onSubmit={handleSearchSubmit} className="flex max-w-md flex-1 items-center gap-2 rounded-full bg-bg-elevated-2 px-4 py-2">
        <Search size={16} className="text-fg-muted" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search artists, albums, songs"
          className="w-full bg-transparent text-sm text-fg-primary outline-none placeholder:text-fg-muted"
        />
      </form>

      <div className="flex items-center gap-3">
        {user?.role === "admin" && (
          <Link href="/settings" className="flex items-center gap-1 text-xs text-fg-secondary hover:text-fg-primary">
            <ShieldCheck size={14} /> Admin
          </Link>
        )}
        <span className="hidden text-sm text-fg-secondary sm:inline">{user?.username}</span>
        <button onClick={logout} className="text-fg-secondary hover:text-fg-primary" aria-label="Log out">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
