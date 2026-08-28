import { cn } from "@/lib/utils";

type BadgeTone = "primary" | "success" | "warning" | "neutral";

const TONE_CLASSES: Record<BadgeTone, string> = {
  primary: "bg-primary-50 text-primary-700",
  success: "bg-success-light text-success",
  warning: "bg-warning-light text-warning",
  neutral: "bg-surface-muted text-muted",
};

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: BadgeTone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        TONE_CLASSES[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
