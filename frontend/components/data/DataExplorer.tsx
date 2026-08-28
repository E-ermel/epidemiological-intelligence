"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import type { EpidemiologicalRecord } from "@/types/data";
import { Card } from "@/components/ui/Card";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ApiError } from "@/services/api";
import { queryEpidemiologicalData } from "@/services/dataService";
import { DISEASES } from "@/lib/constants";
import { formatDate, formatNumber } from "@/lib/utils";

function formatOrDash(value: number | null, formatter: (v: number) => string) {
  return value === null ? "—" : formatter(value);
}

export function DataExplorer() {
  const [disease, setDisease] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [results, setResults] = useState<EpidemiologicalRecord[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const data = await queryEpidemiologicalData({
        disease: disease || undefined,
        municipality: municipality.trim() || undefined,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      });
      setResults(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro inesperado ao consultar os dados.");
      setResults(null);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <Card className="mb-4">
        <form
          onSubmit={handleSearch}
          className="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 lg:grid-cols-5"
        >
          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Doença
            <select
              value={disease}
              onChange={(e) => setDisease(e.target.value)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary-500 focus:outline-none"
            >
              <option value="">Todas</option>
              {DISEASES.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Município
            <input
              value={municipality}
              onChange={(e) => setMunicipality(e.target.value)}
              placeholder="Ex.: Porto Alegre"
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-light focus:border-primary-500 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Data inicial (opcional)
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary-500 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Data final (opcional)
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary-500 focus:outline-none"
            />
          </label>

          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60"
          >
            <Search className="h-4 w-4" />
            Buscar
          </button>
        </form>

        <p className="mt-3 text-xs text-muted-light">
          Todos os campos são independentes -- para filtrar só a partir de uma data, preencha
          apenas &ldquo;Data inicial&rdquo; e deixe &ldquo;Data final&rdquo; em branco (e
          vice-versa).
        </p>
      </Card>

      <Card>
        {isLoading && <LoadingState label="Consultando..." />}

        {!isLoading && error && <ErrorState description={error} />}

        {!isLoading && !error && results === null && (
          <EmptyState
            icon={Search}
            title="Use os filtros acima para consultar"
            description="Todos os campos são opcionais -- deixe em branco para trazer todas as doenças/municípios/período."
          />
        )}

        {!isLoading && !error && results !== null && results.length === 0 && (
          <EmptyState
            title="Nenhum registro encontrado"
            description="Tente ampliar o período ou remover algum filtro."
          />
        )}

        {!isLoading && !error && results !== null && results.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border text-xs font-medium text-muted-light">
                  <th className="whitespace-nowrap py-2 pr-4">Data</th>
                  <th className="whitespace-nowrap py-2 pr-4">Doença</th>
                  <th className="whitespace-nowrap py-2 pr-4">Município</th>
                  <th className="whitespace-nowrap py-2 pr-4 text-right">Casos</th>
                  <th className="whitespace-nowrap py-2 pr-4 text-right">Precipitação (mm)</th>
                  <th className="whitespace-nowrap py-2 text-right">Temp. média (°C)</th>
                </tr>
              </thead>
              <tbody>
                {results.map((record, i) => (
                  <tr
                    key={`${record.disease}-${record.municipality}-${record.referenceDate}-${i}`}
                    className="border-b border-border text-xs last:border-0"
                  >
                    <td className="whitespace-nowrap py-2 pr-4 text-foreground">
                      {formatDate(record.referenceDate)}
                    </td>
                    <td className="whitespace-nowrap py-2 pr-4 text-foreground">{record.disease}</td>
                    <td className="whitespace-nowrap py-2 pr-4 text-foreground">
                      {record.municipality}
                    </td>
                    <td className="whitespace-nowrap py-2 pr-4 text-right text-foreground">
                      {formatOrDash(record.cases, formatNumber)}
                    </td>
                    <td className="whitespace-nowrap py-2 pr-4 text-right text-muted">
                      {formatOrDash(record.precipitationSumMm, (v) => v.toFixed(1))}
                    </td>
                    <td className="whitespace-nowrap py-2 text-right text-muted">
                      {formatOrDash(record.temperatureAvgC, (v) => v.toFixed(1))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
