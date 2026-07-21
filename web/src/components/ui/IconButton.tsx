import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  active?: boolean;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-14 w-14",
};

export function IconButton({ children, active, size = "md", className, ...props }: IconButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-full text-fg-secondary hover:text-fg-primary hover:bg-bg-hover transition-colors duration-150 disabled:opacity-40 disabled:pointer-events-none cursor-pointer",
        active && "text-accent hover:text-accent-hover",
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
