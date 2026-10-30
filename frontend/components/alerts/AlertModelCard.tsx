import type { AlertLevel, AlertModelInfo, AlertOriginType } from "@/types/alert";
import type { DiseaseCode } from "@/types/epidemiology";
import { Card } from "@/components/ui/Card";
import { HOSPITALIZATION_DISEASES } from "@/lib/constants";
import { formatDate, formatMonth } from "@/lib/utils";

const LEVEL_LABELS: Record<AlertLevel, string> = { uf: "Por UF", municipio: "Por município" };

/** "mar. de 2026 (internações) · jul. de 2026 (notificações)" for one origin type. */
export function originLabel(info: AlertModelInfo, originType: AlertOriginType): string {
  const months = new Map<string, string>();
  for (const origin of info.origins.filter((o) => o.originType === originType)) {
    const group = HOSPITALIZATION_DISEASES.includes(origin.disease as DiseaseCode) ? "internações" : "notificações";
    months.set(group, origin.originMonth);
  }
  return ["internações", "notificações"]
    .filter((group) => months.has(group))
    .map((group) => `${formatMonth(months.get(group)!)} (${group})`)
    .join(" · ");
}

function per100(value: number): number {
  return Math.round(value * 100);
}

/**
 * How the alert works and how well it did on the 2024–2025 test, in
 * plain language: precision as "of every 100 alerts, N were outbreaks",
 * recall as "of every 100 outbreaks, N were alerted".
 */
export function AlertModelCard({ info }: { info: AlertModelInfo }) {
  return (
    <Card className="flex flex-col gap-4">
      <div>
        <h2 className="text-sm font-semibold text-foreground">Como o alerta funciona</h2>
        <p className="mt-1 text-xs leading-relaxed text-muted">
          Um mês está em <strong className="font-medium text-foreground">surto</strong> quando os casos passam do canal
          endêmico (média + 1,96 desvio-padrão do mesmo mês nos 5 anos anteriores) e chegam a pelo menos 5 casos na UF ou
          3 no município. O modelo ({info.modelName}) lê a série de casos e o clima dos meses passados e estima a
          probabilidade de surto de 1 a 3 meses à frente. O alerta dispara quando ela passa do corte.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {(Object.keys(LEVEL_LABELS) as AlertLevel[]).map((level) => {
          const metrics = info.testMetrics[level];
          return (
            <div key={level} className="rounded-xl bg-surface-muted p-3 text-xs">
              <p className="font-medium text-foreground">
                {LEVEL_LABELS[level]} · corte {per100(info.cutoffs[level])}%
              </p>
              <ul className="mt-2 space-y-1 text-muted">
                <li>
                  De cada 100 alertas, <strong className="text-foreground">{per100(metrics.precision)}</strong> foram
                  surtos (precisão).
                </li>
                <li>
                  De cada 100 surtos, <strong className="text-foreground">{per100(metrics.recall)}</strong> foram
                  alertados (recall).
                </li>
                <li>
                  F1 {metrics.f1.toFixed(2).replace(".", ",")} · AUC-ROC {metrics.aucRoc.toFixed(2).replace(".", ",")}
                </li>
              </ul>
            </div>
          );
        })}
      </div>

      <div className="space-y-1 border-t border-border pt-3 text-xs text-muted">
        <p>
          <span className="font-medium text-foreground">Mês fechado:</span> parte de {originLabel(info, "fechado")}, o
          último mês com dados completos.
        </p>
        <p>
          <span className="font-medium text-foreground">Provisório:</span> parte de {originLabel(info, "provisorio")},
          com dados ainda incompletos, que tendem a subestimar os casos.
        </p>
        <p className="text-muted-light">
          Métricas do teste em 2024–2025. Rodada de {formatDate(info.runId.slice(0, 10))} ({info.modelVersion}). O alerta
          aprende com a dinâmica recente dos casos e não antecipa surtos causados por eventos repentinos, como enchentes.
        </p>
      </div>
    </Card>
  );
}
