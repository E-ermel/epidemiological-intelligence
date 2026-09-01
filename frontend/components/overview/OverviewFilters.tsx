"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SlidersHorizontal } from "lucide-react";
import type { DiseaseCode } from "@/types/epidemiology";
import { Card } from "@/components/ui/Card";
import { DISEASES } from "@/lib/constants";
import { cn } from "@/lib/utils";

const PERIOD_PRESETS = [
  { label: "Últimos 12 meses", months: 12 },
  { label: "Últimos 5 anos", months: 60 },
] as const;

function isoDateMonthsAgo(months: number): string {
  const date = new Date();
  date.setUTCMonth(date.getUTCMonth() - months);
  return date.toISOString().slice(0, 10);
}

export function OverviewFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [selectedDiseases, setSelectedDiseases] = useState<Set<DiseaseCode>>(
    () => new Set(searchParams.getAll("disease") as DiseaseCode[])
  );
  const [startDate, setStartDate] = useState(searchParams.get("startDate") ?? "");
  const [endDate, setEndDate] = useState(searchParams.get("endDate") ?? "");

  const hasActiveFilters = useMemo(
    () => selectedDiseases.size > 0 || Boolean(startDate) || Boolean(endDate),
    [selectedDiseases, startDate, endDate]
  );

  function toggleDisease(code: DiseaseCode) {
    setSelectedDiseases((prev) => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  }

  function applyPreset(months: number) {
    setStartDate(isoDateMonthsAgo(months));
    setEndDate("");
  }

  function pushFilters(diseases: Set<DiseaseCode>, start: string, end: string) {
    const params = new URLSearchParams();
    diseases.forEach((code) => params.append("disease", code));
    if (start) params.set("startDate", start);
    if (end) params.set("endDate", end);

    const query = params.toString();
    router.push(query ? `${pathname}?${query}` : pathname);
  }

  function handleApply() {
    pushFilters(selectedDiseases, startDate, endDate);
  }

  function handleClear() {
    setSelectedDiseases(new Set());
    setStartDate("");
    setEndDate("");
    router.push(pathname);
  }

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <SlidersHorizontal className="h-4 w-4 text-muted-light" />
          Filtros
        </div>
        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleClear}
            className="text-xs font-medium text-muted hover:text-foreground"
          >
            Limpar filtros
          </button>
        )}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-[2fr_1fr]">
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted">Doenças</p>
          <div className="flex flex-wrap gap-1.5">
            {DISEASES.map(({ code, label }) => (
              <button
                key={code}
                type="button"
                onClick={() => toggleDisease(code)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  selectedDiseases.has(code)
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-border bg-surface text-muted hover:border-border-strong"
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-[11px] text-muted-light">Nenhuma selecionada = todas.</p>
        </div>

        <div>
          <p className="mb-1.5 text-xs font-medium text-muted">Período</p>
          <div className="flex flex-wrap gap-1.5">
            {PERIOD_PRESETS.map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => applyPreset(preset.months)}
                className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted hover:border-border-strong"
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="mt-2 flex items-center gap-2">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-foreground focus:border-primary-500 focus:outline-none"
            />
            <span className="text-xs text-muted-light">até</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-foreground focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={handleApply}
        className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
      >
        Aplicar filtros
      </button>
    </Card>
  );
}
