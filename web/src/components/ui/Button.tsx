import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "outline";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary: "bg-accent text-black font-semibold hover:bg-accent-hover",
  secondary: "bg-bg-elevated-2 text-fg-primary hover:bg-bg-hover",
  ghost: "bg-transparent text-fg-secondary hover:text-fg-primary hover:bg-bg-hover",
  outline: "bg-transparent border border-border-subtle text-fg-primary hover:border-fg-primary",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

export function Button({ variant = "primary", size = "md", className, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full transition-colors duration-150 disabled:opacity-40 disabled:pointer-events-none cursor-pointer",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
