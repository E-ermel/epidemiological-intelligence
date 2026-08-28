import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
}: {
  title: string;
  description?: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-muted text-muted-light">
        <Icon className="h-5 w-5" />
      </span>
      <span className="text-sm font-medium text-foreground">{title}</span>
      {description && <span className="max-w-sm text-xs text-muted">{description}</span>}
    </div>
  );
}
