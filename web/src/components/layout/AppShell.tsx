"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { TopBar } from "./TopBar";
import { BottomPlayer } from "@/components/player/BottomPlayer";
import { AudioEngine } from "@/components/player/AudioEngine";
import { useAuth } from "@/lib/useAuth";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return <div className="flex h-screen w-full items-center justify-center bg-bg-base text-fg-secondary">Loading dtp-tunes…</div>;
  }

  return (
    <div className="flex h-screen w-full flex-col bg-bg-base">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <TopBar />
          <main className="scrollbar-none flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>
      <BottomPlayer />
      <MobileNav />
      <AudioEngine />
    </div>
  );
}
