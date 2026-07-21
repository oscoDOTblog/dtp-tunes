import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-center px-6">
      {icon && <div className="text-fg-muted">{icon}</div>}
      <p className="text-lg font-semibold text-fg-primary">{title}</p>
      {description && <p className="text-sm text-fg-secondary max-w-sm">{description}</p>}
      {action}
    </div>
  );
}
