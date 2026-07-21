import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-lg bg-bg-elevated-2 border border-border-subtle px-4 text-sm text-fg-primary placeholder:text-fg-muted outline-none focus:border-accent transition-colors",
        className
      )}
      {...props}
    />
  );
}
