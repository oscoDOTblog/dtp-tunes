"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Play, Download } from "lucide-react";
import type { Album } from "@/lib/types";
import { albumDownloadUrl, coverUrl, downloadFile } from "@/lib/api";
import { ContextMenu, MenuItem, type ContextMenuPosition } from "@/components/ui/Menu";
import { useToast } from "@/components/ui/ToastProvider";

export function AlbumCard({ album }: { album: Album }) {
  const [contextPos, setContextPos] = useState<ContextMenuPosition | null>(null);
  const [downloading, setDownloading] = useState(false);
  const toast = useToast();

  async function handleDownload() {
    if (downloading) return;
    setDownloading(true);
    try {
      await downloadFile(albumDownloadUrl(album.id), `${album.name}.zip`);
      toast.success("Album download started");
    } catch {
      toast.error("Failed to download album");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <>
      <div
        onContextMenu={(event) => {
          event.preventDefault();
          setContextPos({ x: event.clientX, y: event.clientY });
        }}
      >
        <Link
          href={`/album/${album.id}`}
          className="group relative flex flex-col gap-3 rounded-xl bg-bg-elevated p-4 transition-colors duration-150 hover:bg-bg-elevated-2"
        >
          <div className="relative aspect-square overflow-hidden rounded-lg bg-bg-elevated-2 shadow-lg">
            <Image
              src={coverUrl(album.coverArtId, 300)}
              alt={album.name}
              fill
              sizes="200px"
              className="object-cover"
              unoptimized
            />
            <div className="absolute bottom-2 right-2 flex h-11 w-11 translate-y-2 items-center justify-center rounded-full bg-accent text-black opacity-0 shadow-xl transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100">
              <Play size={18} fill="black" />
            </div>
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-fg-primary">{album.name}</p>
            <p className="truncate text-xs text-fg-secondary">
              {album.year ? `${album.year} · ` : ""}
              {album.artistName ?? "Unknown Artist"}
            </p>
          </div>
        </Link>
      </div>

      <ContextMenu position={contextPos} onClose={() => setContextPos(null)}>
        <MenuItem onClick={handleDownload} disabled={downloading}>
          <Download size={16} />
          {downloading ? "Downloading…" : "Download"}
        </MenuItem>
      </ContextMenu>
    </>
  );
}
