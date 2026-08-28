import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { StudySummary } from "@/types/study";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatNumber } from "@/lib/utils";

export function StudyCard({ study }: { study: StudySummary }) {
  return (
    <Card className="flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{study.label}</h3>
        <Badge tone="primary">{study.activeModelVersion}</Badge>
      </div>

      <p className="flex-1 text-xs leading-relaxed text-muted">{study.description}</p>

      <div className="flex items-center justify-between border-t border-border pt-3 text-xs">
        <div>
          <p className="font-medium text-foreground">{formatNumber(study.totalCases)}</p>
          <p className="text-muted-light">casos</p>
        </div>
        <div>
          <p className="font-medium text-foreground">{study.municipalityCount}</p>
          <p className="text-muted-light">municípios</p>
        </div>
        <Link
          href={`/modelos?disease=${encodeURIComponent(study.disease)}`}
          className="flex items-center gap-1 font-medium text-primary-600 hover:text-primary-700"
        >
          Ver modelo
          <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </Card>
  );
}
