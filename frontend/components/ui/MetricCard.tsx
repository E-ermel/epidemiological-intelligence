import type { LucideIcon } from "lucide-react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn, formatPercent } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  trendPct?: number | null;
  trendLabel?: string;
}

export function MetricCard({ label, value, icon: Icon, trendPct, trendLabel }: MetricCardProps) {
  const hasTrend = typeof trendPct === "number";
  const isPositive = hasTrend && trendPct >= 0;

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted">{label}</span>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-50 text-primary-600">
          <Icon className="h-4 w-4" strokeWidth={2} />
        </span>
      </div>

      <span className="text-2xl font-semibold tracking-tight text-foreground">{value}</span>

      {hasTrend && (
        <div className="flex items-center gap-1 text-xs">
          <span
            className={cn(
              "flex items-center gap-0.5 font-medium",
              isPositive ? "text-success" : "text-danger"
            )}
          >
            {isPositive ? (
              <TrendingUp className="h-3.5 w-3.5" />
            ) : (
              <TrendingDown className="h-3.5 w-3.5" />
            )}
            {formatPercent(Math.abs(trendPct))}
          </span>
          {trendLabel && <span className="text-muted-light">{trendLabel}</span>}
        </div>
      )}
    </Card>
  );
}
