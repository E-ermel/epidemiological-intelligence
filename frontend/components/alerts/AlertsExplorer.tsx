"use client";

import { useRef, useState } from "react";
import type { AlertOriginType, AlertRecord, AlertStateSummary } from "@/types/alert";
import { AlertStateMap } from "@/components/alerts/AlertStateMap";
import { AlertsTable } from "@/components/alerts/AlertsTable";
import { Card } from "@/components/ui/Card";
import { LoadingState } from "@/components/ui/LoadingState";
import { getAlerts, getAlertStates } from "@/services/api";
import { DISEASES, STATES } from "@/lib/constants";
import { cn } from "@/lib/utils";

const ORIGINS: { value: AlertOriginType; label: string; hint: string }[] = [
  { value: "fechado", label: "Mês fechado", hint: "Parte do último mês com dados completos (mais confiável)." },
  { value: "provisorio", label: "Provisório", hint: "Parte do último mês disponível, com dados ainda incompletos." },
];
const HORIZONS = [1, 2, 3];
// Oropouche não tem alerta (poucos casos para um canal endêmico).
const ALERT_DISEASES = DISEASES.filter((d) => d.code !== "OROPOUCHE");

interface AlertsExplorerProps {
  initialStates: AlertStateSummary[];
  initialRows: AlertRecord[];
}

function Segmented<T extends string | number>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-border bg-surface-muted p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
            option.value === value ? "bg-surface text-foreground shadow-sm" : "text-muted hover:text-foreground"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Filters (origin, horizon, disease) drive both the state map and the
 * table; each change refetches both (update()). With no state selected the table lists the states in alert
 * across Brazil; clicking a state lists that state's alert and its
 * municipalities in alert.
 */
export function AlertsExplorer({ initialStates, initialRows }: AlertsExplorerProps) {
  const [originType, setOriginType] = useState<AlertOriginType>("fechado");
  const [horizon, setHorizon] = useState(1);
  const [disease, setDisease] = useState("");
  const [selectedState, setSelectedState] = useState<string | undefined>();
  const [states, setStates] = useState(initialStates);
  const [rows, setRows] = useState(initialRows);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(false);
  // Ignores a slow response for filters the user already changed.
  const latestRequest = useRef(0);

  function update(next: {
    originType?: AlertOriginType;
    horizon?: number;
    disease?: string;
    selectedState?: string | null;
  }) {
    const filters = {
      originType: next.originType ?? originType,
      horizon: next.horizon ?? horizon,
      disease: next.disease ?? disease,
      selectedState: next.selectedState === null ? undefined : (next.selectedState ?? selectedState),
    };
    setOriginType(filters.originType);
    setHorizon(filters.horizon);
    setDisease(filters.disease);
    setSelectedState(filters.selectedState);

    const request = ++latestRequest.current;
    const common = {
      originType: filters.originType,
      horizon: filters.horizon,
      disease: filters.disease || undefined,
    };
    setIsLoading(true);
    setError(false);

    const tableRows = filters.selectedState
      ? Promise.all([
          getAlerts({ ...common, level: "uf", state: filters.selectedState }),
          getAlerts({ ...common, level: "municipio", state: filters.selectedState, onlyAlerts: true, limit: 300 }),
        ]).then(([uf, municipalities]) => [...uf, ...municipalities])
      : getAlerts({ ...common, level: "uf", onlyAlerts: true, limit: 300 });

    Promise.all([getAlertStates(common.originType, common.horizon, common.disease), tableRows])
      .then(([nextStates, nextRows]) => {
        if (request !== latestRequest.current) return;
        setStates(nextStates);
        setRows(nextRows);
      })
      .catch(() => {
        if (request === latestRequest.current) setError(true);
      })
      .finally(() => {
        if (request === latestRequest.current) setIsLoading(false);
      });
  }

  const stateName = STATES.find((s) => s.code === selectedState)?.name;
  const origin = ORIGINS.find((o) => o.value === originType);

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-muted">Ponto de partida</span>
          <Segmented options={ORIGINS} value={originType} onChange={(value) => update({ originType: value })} />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-muted">Previsão para</span>
          <Segmented
            options={HORIZONS.map((h) => ({ value: h, label: h === 1 ? "1 mês à frente" : `${h} meses` }))}
            value={horizon}
            onChange={(value) => update({ horizon: value })}
          />
        </div>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-muted">Doença</span>
          <select
            value={disease}
            onChange={(event) => update({ disease: event.target.value })}
            className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-foreground"
          >
            <option value="">Todas</option>
            {ALERT_DISEASES.map((d) => (
              <option key={d.code} value={d.code}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
        <p className="basis-full text-xs text-muted-light">{origin?.hint}</p>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <h2 className="mb-2 text-sm font-semibold text-foreground">Risco de surto por UF</h2>
          <AlertStateMap
            states={states}
            selectedState={selectedState}
            onSelectState={(state) => update({ selectedState: state ?? null })}
          />
        </Card>

        <Card className="lg:col-span-3">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-foreground">
              {selectedState ? `Alertas em ${stateName}` : "UFs em alerta"}
            </h2>
            {selectedState && (
              <button
                type="button"
                onClick={() => update({ selectedState: null })}
                className="text-xs font-medium text-primary-600 hover:text-primary-700"
              >
                Ver o Brasil
              </button>
            )}
          </div>
          {isLoading ? (
            <LoadingState label="Carregando alertas..." />
          ) : error ? (
            <p className="py-8 text-center text-sm text-muted">Não foi possível carregar os alertas.</p>
          ) : (
            <AlertsTable
              rows={rows}
              emptyMessage={
                selectedState
                  ? "Sem previsão para esta UF com estes filtros."
                  : "Nenhuma UF em alerta com estes filtros."
              }
            />
          )}
          {!selectedState && !isLoading && (
            <p className="mt-3 text-xs text-muted-light">Clique em uma UF no mapa para ver os municípios em alerta.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
