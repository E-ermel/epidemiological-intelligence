import { Activity, CalendarRange, MapPinned, Stethoscope } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { EpidemiologicalChart } from "@/components/charts/EpidemiologicalChart";
import { DiseaseDistributionChart } from "@/components/charts/DiseaseDistributionChart";
import { OverviewMap } from "@/components/map/OverviewMap";
import { getCaseCurve, getDiseaseDistribution, getOverviewMetrics } from "@/services/overviewService";
import { getMapBubbles } from "@/services/geographyService";
import { formatDate, formatNumber } from "@/lib/utils";

export default async function OverviewPage() {
  const [metrics, caseCurve, distribution, countryBubbles, rsBubbles] = await Promise.all([
    getOverviewMetrics(),
    getCaseCurve(),
    getDiseaseDistribution(),
    getMapBubbles("country"),
    getMapBubbles("state", "RS"),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
          Visão Geral
        </h1>
        <p className="mt-1 text-sm text-muted">
          {formatDate(metrics.periodStart)} – {formatDate(metrics.periodEnd)}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Casos analisados"
          value={formatNumber(metrics.totalCases)}
          icon={Activity}
          trendPct={metrics.totalCasesTrendPct}
          trendLabel="vs. período anterior"
        />
        <MetricCard label="Municípios" value={String(metrics.municipalityCount)} icon={MapPinned} />
        <MetricCard label="Doenças monitoradas" value={String(metrics.diseaseCount)} icon={Stethoscope} />
        <MetricCard
          label="Período"
          value={`${new Date(metrics.periodStart).getFullYear()}–${new Date(metrics.periodEnd).getFullYear()}`}
          icon={CalendarRange}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <h2 className="mb-1 text-sm font-semibold text-foreground">Curva epidemiológica</h2>
            <p className="mb-2 text-xs text-muted">Casos por mês, todas as doenças monitoradas.</p>
            <EpidemiologicalChart data={caseCurve} />
          </Card>

          <Card>
            <h2 className="mb-1 text-sm font-semibold text-foreground">Distribuição por doença</h2>
            <p className="mb-2 text-xs text-muted">Participação no total de casos do período.</p>
            <DiseaseDistributionChart data={distribution} />
            <ul className="mt-2 flex flex-col gap-1.5">
              {distribution.map((slice) => (
                <li key={slice.disease} className="flex items-center justify-between text-xs">
                  <span className="text-muted">{slice.label}</span>
                  <span className="font-medium text-foreground">
                    {slice.shareOfTotalPct.toFixed(1)}%
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <Card className="lg:col-span-3">
          <h2 className="mb-1 text-sm font-semibold text-foreground">Mapa</h2>
          <p className="mb-2 text-xs text-muted">
            Casos por região. Clique em um estado para explorar os municípios.
          </p>
          <OverviewMap countryBubbles={countryBubbles} stateBubbles={{ RS: rsBubbles }} />
        </Card>
      </div>
    </div>
  );
}
