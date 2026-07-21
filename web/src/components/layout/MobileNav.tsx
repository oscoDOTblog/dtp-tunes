"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Search, Library, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/", label: "Home", icon: Home },
  { href: "/search", label: "Search", icon: Search },
  { href: "/library", label: "Library", icon: Library },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="flex h-16 flex-shrink-0 items-center justify-around border-t border-border-subtle bg-bg-elevated md:hidden">
      {items.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={cn("flex flex-col items-center gap-1 text-xs", active ? "text-accent" : "text-fg-secondary")}
          >
            <Icon size={22} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
