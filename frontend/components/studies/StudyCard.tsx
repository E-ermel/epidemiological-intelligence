import { Maximize2 } from "lucide-react";
import type { StudySummary } from "@/types/study";
import { Badge } from "@/components/ui/Badge";
import { formatNumber } from "@/lib/utils";

/** UFs em alerta de surto nos próximos 3 meses (origem "fechado"). */
function AlertBadge({ statesInAlert }: { statesInAlert: number | null }) {
  if (statesInAlert === null) return <Badge tone="neutral">sem alerta</Badge>;
  if (statesInAlert === 0) return <Badge tone="success">nenhuma UF em alerta</Badge>;
  return (
    <Badge tone="warning">
      {statesInAlert} {statesInAlert === 1 ? "UF em alerta" : "UFs em alerta"}
    </Badge>
  );
}

export function StudyCard({
  study,
  onExpand,
}: {
  study: StudySummary;
  onExpand: (anchor: DOMRect) => void;
}) {
  return (
    <button
      type="button"
      onClick={(event) => onExpand(event.currentTarget.getBoundingClientRect())}
      className="flex h-full w-full flex-col gap-3 rounded-2xl border border-border bg-surface p-5 text-left shadow-[var(--shadow-card)] transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{study.label}</h3>
        <AlertBadge statesInAlert={study.statesInAlert} />

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
        <span className="flex items-center gap-1 font-medium text-primary-600">
          Explorar
          <Maximize2 className="h-3.5 w-3.5" />
        </span>
      </div>
    </button>
  );
}
