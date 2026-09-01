"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Search, X } from "lucide-react";
import type { StudySummary } from "@/types/study";
import type { EpidemiologicalRecord } from "@/types/data";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ClimateTrendChart } from "@/components/charts/ClimateTrendChart";
import { SeasonalityChart } from "@/components/charts/SeasonalityChart";
import { MunicipalityCasesChart } from "@/components/charts/MunicipalityCasesChart";
import { queryEpidemiologicalData } from "@/services/dataService";
import { ApiError } from "@/services/api";
import {
  aggregateByMonth,
  aggregateByMunicipality,
  aggregateSeasonality,
} from "@/lib/aggregateEpidemiologicalRecords";
import { CLIMATE_VARIABLES } from "@/lib/constants";
import { cn, formatNumber } from "@/lib/utils";

const TRANSITION_MS = 200;

export function StudyDashboardModal({
  study,
  anchorRect,
  municipalities,
  onClose,
}: {
  study: StudySummary;
  anchorRect: DOMRect;
  municipalities: string[];
  onClose: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const [municipality, setMunicipality] = useState("");
  const [climateKey, setClimateKey] = useState(CLIMATE_VARIABLES[0].key);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [records, setRecords] = useState<EpidemiologicalRecord[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setIsExpanded(true));

    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") handleClose();
    }
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchData() {
    setIsLoading(true);
    setError(null);

    try {
      const data = await queryEpidemiologicalData({
        disease: study.disease,
        municipality: municipality || undefined,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      });
      setRecords(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro inesperado ao consultar os dados.");
      setRecords(null);
    } finally {
      setIsLoading(false);
    }
  }

  function handleClose() {
    setIsExpanded(false);
    setTimeout(onClose, TRANSITION_MS);
  }

  const climateLabel = CLIMATE_VARIABLES.find((v) => v.key === climateKey)?.label ?? "";
  const trendData = records ? aggregateByMonth(records, climateKey) : [];
  const seasonalityData = records ? aggregateSeasonality(records) : [];
  const municipalityData = records ? aggregateByMunicipality(records) : [];
  const totalCases = records?.reduce((sum, r) => sum + (r.cases ?? 0), 0) ?? 0;
  const municipalityCount = records ? new Set(records.map((r) => r.municipality)).size : 0;

  const collapsedStyle: React.CSSProperties = {
    top: anchorRect.top,
    left: anchorRect.left,
    width: anchorRect.width,
    height: anchorRect.height,
  };

  const expandedStyle: React.CSSProperties = {
    top: "3vh",
    left: "3vw",
    width: "94vw",
    height: "94vh",
  };

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        className={cn(
          "absolute inset-0 bg-slate-900/40 transition-opacity",
          isExpanded ? "opacity-100" : "opacity-0"
        )}
        style={{ transitionDuration: `${TRANSITION_MS}ms` }}
        onClick={handleClose}
      />

      <div
        style={isExpanded ? expandedStyle : collapsedStyle}
        className={cn(
          "fixed flex flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-xl transition-all ease-out"
        )}
      >
        {/* Fade the real content in only once the panel is roughly full-size --
            a tiny card can't meaningfully show a dashboard mid-transition. */}
        <div
          className={cn(
            "flex min-h-0 flex-1 flex-col transition-opacity delay-100",
            isExpanded ? "opacity-100" : "opacity-0"
          )}
          style={{ transitionDuration: `${TRANSITION_MS}ms` }}
        >
          <div className="flex items-start justify-between gap-3 border-b border-border p-5">
            <div>
              <h2 className="text-lg font-semibold text-foreground">{study.label}</h2>
              <p className="mt-0.5 text-xs text-muted">{study.description}</p>
            </div>
            <button
              type="button"
              onClick={handleClose}
              className="rounded-full p-1.5 text-muted hover:bg-surface-muted hover:text-foreground"
              aria-label="Fechar"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                fetchData();
              }}
              className="mb-4 grid grid-cols-1 items-end gap-3 rounded-xl border border-border bg-surface-muted p-3 sm:grid-cols-2 lg:grid-cols-5"
            >
              <label className="flex flex-col gap-1 text-xs font-medium text-muted">
                Município
                <select
                  value={municipality}
                  onChange={(e) => setMunicipality(e.target.value)}
                  className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-sm text-foreground focus:border-primary-500 focus:outline-none"
                >
                  <option value="">Todos</option>
                  {municipalities.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-1 text-xs font-medium text-muted">
                Variável climática
                <select
                  value={climateKey}
                  onChange={(e) => setClimateKey(e.target.value as typeof climateKey)}
                  className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-sm text-foreground focus:border-primary-500 focus:outline-none"
                >
                  {CLIMATE_VARIABLES.map((v) => (
                    <option key={v.key} value={v.key}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-1 text-xs font-medium text-muted">
                Data inicial
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-sm text-foreground focus:border-primary-500 focus:outline-none"
                />
              </label>

              <label className="flex flex-col gap-1 text-xs font-medium text-muted">
                Data final
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-sm text-foreground focus:border-primary-500 focus:outline-none"
                />
              </label>

              <button
                type="submit"
                disabled={isLoading}
                className="flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60"
              >
                <Search className="h-4 w-4" />
                Aplicar
              </button>
            </form>

            {isLoading && <LoadingState label="Consultando..." />}
            {!isLoading && error && <ErrorState description={error} />}

            {!isLoading && !error && records && (
              <div className="flex flex-col gap-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-border p-3">
                    <p className="text-xs text-muted-light">Casos no período</p>
                    <p className="text-lg font-semibold text-foreground">
                      {formatNumber(totalCases)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-border p-3">
                    <p className="text-xs text-muted-light">Municípios</p>
                    <p className="text-lg font-semibold text-foreground">
                      {formatNumber(municipalityCount)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-border p-3">
                    <p className="text-xs text-muted-light">Registros</p>
                    <p className="text-lg font-semibold text-foreground">
                      {formatNumber(records.length)}
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-border p-4">
                  <h3 className="mb-1 text-sm font-semibold text-foreground">
                    Casos × {climateLabel}
                  </h3>
                  <p className="mb-2 text-xs text-muted">
                    Casos (esquerda) e {climateLabel.toLowerCase()} (direita), por mês.
                  </p>
                  <ClimateTrendChart data={trendData} variableLabel={climateLabel} />
                </div>

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <div className="rounded-xl border border-border p-4">
                    <h3 className="mb-1 text-sm font-semibold text-foreground">Sazonalidade</h3>
                    <p className="mb-2 text-xs text-muted">
                      Média de casos por mês do calendário, em todos os anos do período.
                    </p>
                    <SeasonalityChart data={seasonalityData} />
                  </div>

                  {!municipality && municipalityData.length > 0 && (
                    <div className="rounded-xl border border-border p-4">
                      <h3 className="mb-1 text-sm font-semibold text-foreground">
                        Municípios com mais casos
                      </h3>
                      <p className="mb-2 text-xs text-muted">
                        Top {municipalityData.length} no período filtrado.
                      </p>
                      <MunicipalityCasesChart data={municipalityData} />
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
