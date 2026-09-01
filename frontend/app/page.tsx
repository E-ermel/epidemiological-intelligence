import { Activity, CalendarRange, MapPinned, Stethoscope } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { EpidemiologicalChart } from "@/components/charts/EpidemiologicalChart";
import { DiseaseDistributionChart } from "@/components/charts/DiseaseDistributionChart";
import { OverviewMap } from "@/components/map/OverviewMap";
import { OverviewFilters } from "@/components/overview/OverviewFilters";
import { getOverviewData } from "@/services/overviewService";
import { getCountryAreas, getMunicipalityBubbles } from "@/services/geographyService";
import { formatDate, formatNumber } from "@/lib/utils";

// Data comes from a live backend now, not a build-time mock -- must
// be fetched per-request, not baked in at `next build` time.
export const dynamic = "force-dynamic";

interface OverviewPageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function OverviewPage({ searchParams }: OverviewPageProps) {
  const params = await searchParams;
  const diseaseParam = params.disease;
  const diseases = diseaseParam === undefined
    ? []
    : Array.isArray(diseaseParam)
      ? diseaseParam
      : [diseaseParam];
  const startDate = typeof params.startDate === "string" ? params.startDate : undefined;
  const endDate = typeof params.endDate === "string" ? params.endDate : undefined;

  const mapFilters = { diseases, startDate, endDate };

  const [{ metrics, caseCurve, diseaseDistribution: distribution }, countryAreas, rsBubbles] =
    await Promise.all([
      getOverviewData(mapFilters),
      getCountryAreas(mapFilters),
      getMunicipalityBubbles("RS", mapFilters),
    ]);

  const periodLabel = metrics.periodStart && metrics.periodEnd
    ? `${new Date(metrics.periodStart).getUTCFullYear()}–${new Date(metrics.periodEnd).getUTCFullYear()}`
    : "—";

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

      <OverviewFilters />

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
        <MetricCard label="Período" value={periodLabel} icon={CalendarRange} />
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
          <OverviewMap countryAreas={countryAreas} stateBubbles={{ RS: rsBubbles }} />
        </Card>
      </div>
    </div>
  );
}
