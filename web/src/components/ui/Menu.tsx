"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

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
          className={cn(
            "absolute top-full z-40 mt-1 min-w-48 overflow-hidden rounded-lg border border-border-subtle bg-bg-elevated py-1 shadow-xl",
            align === "right" ? "right-0" : "left-0"
          )}
        >
          <div onClick={() => setOpen(false)}>{children}</div>
        </div>
      )}
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
