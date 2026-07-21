"use client";

import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

const PANEL_CLASSES =
  "z-40 min-w-48 overflow-hidden rounded-lg border border-border-subtle bg-bg-elevated py-1 shadow-xl";

interface MenuProps {
  trigger: ReactNode;
  children: ReactNode;
  align?: "left" | "right";
  className?: string;
}

/** Lightweight anchored dropdown: outside-click + Escape to close. */
export function Menu({ trigger, children, align = "right", className }: MenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className={cn("relative inline-flex", className)}>
      <div
        onClick={(event) => {
          event.stopPropagation();
          setOpen((value) => !value);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setOpen((value) => !value);
          }
        }}
      >
        {trigger}
      </div>
      {open && (
        <div
          id={menuId}
          role="menu"
          className={cn("absolute top-full mt-1", PANEL_CLASSES, align === "right" ? "right-0" : "left-0")}
        >
          <div onClick={() => setOpen(false)}>{children}</div>
        </div>
      )}
    </div>
  );
}

export interface ContextMenuPosition {
  x: number;
  y: number;
}

interface ContextMenuProps {
  position: ContextMenuPosition | null;
  onClose: () => void;
  children: ReactNode;
}

/**
 * Cursor-anchored menu for right-click, Spotify-style. Render with a
 * position from the contextmenu event; clamped to the viewport.
 */
export function ContextMenu({ position, onClose, children }: ContextMenuProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Clamp to the viewport by measuring the rendered panel and adjusting its
  // style directly — avoids a second render pass.
  useLayoutEffect(() => {
    const panel = panelRef.current;
    if (!position || !panel) return;
    const x = Math.max(8, Math.min(position.x, window.innerWidth - panel.offsetWidth - 8));
    const y = Math.max(8, Math.min(position.y, window.innerHeight - panel.offsetHeight - 8));
    panel.style.left = `${x}px`;
    panel.style.top = `${y}px`;
  }, [position]);

  useEffect(() => {
    if (!position) return;

    function onPointerDown(event: MouseEvent) {
      if (!panelRef.current?.contains(event.target as Node)) onClose();
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("scroll", onClose, true);
    window.addEventListener("resize", onClose);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("scroll", onClose, true);
      window.removeEventListener("resize", onClose);
    };
  }, [position, onClose]);

  if (!position) return null;

  return (
    <div
      ref={panelRef}
      role="menu"
      style={{ left: position.x, top: position.y }}
      className={cn("fixed", PANEL_CLASSES)}
      onClick={onClose}
      onContextMenu={(event) => event.preventDefault()}
    >
      {children}
    </div>
  );
}

interface MenuItemProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
}

export function MenuItem({ children, className, ...props }: MenuItemProps) {
  return (
    <button
      role="menuitem"
      type="button"
      className={cn(
        "flex w-full items-center gap-3 px-3 py-2 text-left text-sm text-fg-primary transition-colors hover:bg-bg-hover disabled:pointer-events-none disabled:opacity-40",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
