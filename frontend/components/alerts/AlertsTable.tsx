import type { AlertRecord } from "@/types/alert";
import type { DiseaseCode } from "@/types/epidemiology";
import { Badge } from "@/components/ui/Badge";
import { DISEASE_LABELS } from "@/lib/constants";
import { formatMonth, formatNumber, formatProbability } from "@/lib/utils";

function place(row: AlertRecord): string {
  return row.level === "municipio" ? `${row.municipalityName ?? row.municipalityCode} (${row.state})` : row.state;
}

function observed(row: AlertRecord): string {
  if (row.observedCases === null) return "—";
  return `${formatNumber(Math.round(row.observedCases))}${row.targetProvisional ? "*" : ""}`;
}

/**
 * One row per series × target month: outbreak probability (with the
 * alert cutoff as a tick on the bar), expected cases (median and 80%
 * range) against the outbreak limit, and cases already reported.
 * Scrolling is left to the parent; the header sticks to its top.
 */
export function AlertsTable({ rows, emptyMessage, color }: { rows: AlertRecord[]; emptyMessage: string; color: string }) {
  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-muted">{emptyMessage}</p>;
  }

  const hasProvisional = rows.some((row) => row.targetProvisional && row.observedCases !== null);

  return (
    <div>
      <table className="w-full min-w-[720px] text-left text-xs">
        <thead className="sticky top-0 z-10 bg-surface text-muted shadow-[inset_0_-1px_0_var(--color-border)]">
          <tr>
            <th className="py-2 pr-3 font-medium">Doença</th>
            <th className="py-2 pr-3 font-medium">Local</th>
            <th className="py-2 pr-3 font-medium">Mês previsto</th>
            <th className="py-2 pr-3 font-medium">Probabilidade de surto</th>
            <th className="py-2 pr-3 text-right font-medium">Casos esperados (faixa)</th>
            <th className="py-2 pr-3 text-right font-medium">Limite de surto</th>
            <th className="py-2 pr-3 text-right font-medium">Já registrados</th>
            <th className="py-2 font-medium" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={`${row.level}-${row.disease}-${row.state}-${row.municipalityCode}-${row.targetMonth}`}
              className="border-b border-border/60 last:border-0"
            >
              <td className="py-2 pr-3 text-foreground">{DISEASE_LABELS[row.disease as DiseaseCode] ?? row.disease}</td>
              <td className="py-2 pr-3 text-foreground">{place(row)}</td>
              <td className="whitespace-nowrap py-2 pr-3 text-muted">{formatMonth(row.targetMonth)}</td>
              <td className="py-2 pr-3">
                <div className="flex items-center gap-2">
                  <div className="relative h-1.5 w-24 rounded-full bg-surface-muted">
                    <div
                      className="h-1.5 rounded-full"
                      style={{
                        width: `${Math.round(row.probability * 100)}%`,
                        background: color,
                        opacity: row.alert ? 0.85 : 0.35,
                      }}
                    />
                    <div
                      className="absolute -top-0.5 h-2.5 w-px bg-foreground"
                      style={{ left: `${row.cutoff * 100}%` }}
                      title={`Corte do alerta: ${formatProbability(row.cutoff)}`}
                    />
                  </div>
                  <span className="font-medium text-foreground">{formatProbability(row.probability)}</span>
                </div>
              </td>
              <td className="py-2 pr-3 text-right text-foreground">
                {formatNumber(Math.round(row.casesP50))}{" "}
                <span className="text-muted-light">
                  ({formatNumber(Math.round(row.casesP10))}–{formatNumber(Math.round(row.casesP90))})
                </span>
              </td>
              <td className="py-2 pr-3 text-right text-muted">{formatNumber(Math.round(row.threshold))}</td>
              <td className="py-2 pr-3 text-right text-muted">{observed(row)}</td>
              <td className="py-2">{row.alert ? <Badge tone="warning">alerta</Badge> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {hasProvisional && (
        <p className="mt-2 text-xs text-muted-light">* dados ainda provisórios para o mês: o número pode subir.</p>
      )}
    </div>
  );
}
