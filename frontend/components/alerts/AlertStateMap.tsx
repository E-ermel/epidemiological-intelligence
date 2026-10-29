"use client";

import { useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { AlertStateSummary } from "@/types/alert";
import { IBGE_CODAREA_TO_UF } from "@/components/map/ibgeStateCodes";
import brazilStatesGeoJson from "@/data/geo/brasil-uf.json";
import { formatProbability } from "@/lib/utils";

/**
 * Choropleth of the outbreak alert by state: each state is shaded by the
 * highest outbreak probability among its diseases (or the selected one),
 * in one hue from light to dark. States with at least one disease above
 * the alert cutoff get an outline. Clicking a state selects it.
 */

const VIEWBOX_WIDTH = 460;
const VIEWBOX_HEIGHT = 480;

type StateFeature = Feature<Geometry, { codarea: string }>;

const STATES_GEOJSON = brazilStatesGeoJson as unknown as FeatureCollection<Geometry, { codarea: string }>;
const PATH = geoPath(geoMercator().fitSize([VIEWBOX_WIDTH, VIEWBOX_HEIGHT], STATES_GEOJSON));

/** Probability bins (upper bounds) and the shade of each, one hue light -> dark. */
export const PROBABILITY_BINS = [
  { upTo: 0.1, label: "0–10%", opacity: 0.08 },
  { upTo: 0.2, label: "10–20%", opacity: 0.22 },
  { upTo: 0.3, label: "20–30%", opacity: 0.38 },
  { upTo: 0.5, label: "30–50%", opacity: 0.6 },
  { upTo: 1.01, label: "50–100%", opacity: 0.85 },
];

function shade(probability: number | null): number | null {
  if (probability === null) return null;
  return PROBABILITY_BINS.find((bin) => probability < bin.upTo)?.opacity ?? 0.85;
}

interface AlertStateMapProps {
  states: AlertStateSummary[];
  selectedState?: string;
  onSelectState: (state: string | undefined) => void;
}

export function AlertStateMap({ states, selectedState, onSelectState }: AlertStateMapProps) {
  const [hovered, setHovered] = useState<{ summary: AlertStateSummary; x: number; y: number } | null>(null);
  const byState = useMemo(() => new Map(states.map((s) => [s.state, s])), [states]);

  return (
    <div>
      <div className="relative">
        <svg
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
          className="w-full"
          style={{ maxHeight: 520 }}
          role="img"
          aria-label="Mapa do Brasil com a probabilidade de surto por UF"
        >
          {STATES_GEOJSON.features.map((feature: StateFeature) => {
            const uf = IBGE_CODAREA_TO_UF[feature.properties.codarea];
            const summary = uf ? byState.get(uf) : undefined;
            const opacity = shade(summary?.maxProbability ?? null);
            const inAlert = (summary?.stateAlerts ?? 0) > 0;
            const isSelected = uf !== undefined && uf === selectedState;
            const [cx, cy] = PATH.centroid(feature);

            return (
              <path
                key={feature.properties.codarea}
                d={PATH(feature) ?? undefined}
                fill={opacity === null ? "var(--color-border-strong)" : "var(--color-danger)"}
                fillOpacity={opacity ?? 0.35}
                stroke={
                  isSelected ? "var(--color-primary-700)" : inAlert ? "var(--color-foreground)" : "var(--color-surface)"
                }
                strokeWidth={isSelected ? 2.5 : inAlert ? 1.4 : 1}
                className="cursor-pointer transition-opacity hover:opacity-80"
                onMouseEnter={() => summary && setHovered({ summary, x: cx, y: cy })}
                onMouseLeave={() => setHovered(null)}
                onClick={() => uf && onSelectState(isSelected ? undefined : uf)}
              >
                <title>{summary ? `${summary.name}: ${describe(summary)}` : uf}</title>
              </path>
            );
          })}
        </svg>

        {hovered && (
          <div className="pointer-events-none absolute left-3 top-3 rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-[var(--shadow-card)]">
            <p className="font-medium text-foreground">{hovered.summary.name}</p>
            <p className="text-muted">{describe(hovered.summary)}</p>
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
        <span className="font-medium text-foreground">Maior probabilidade de surto</span>
        {PROBABILITY_BINS.map((bin) => (
          <span key={bin.label} className="flex items-center gap-1.5">
            <span
              className="h-3 w-5 rounded-sm"
              style={{ background: "var(--color-danger)", opacity: bin.opacity }}
            />
            {bin.label}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-5 rounded-sm border-[1.5px] border-foreground" />
          UF com doença em alerta
        </span>
      </div>
    </div>
  );
}

function describe(summary: AlertStateSummary): string {
  const probability =
    summary.maxProbability === null ? "sem previsão" : `até ${formatProbability(summary.maxProbability)}`;
  const diseases = summary.stateAlerts === 1 ? "1 doença em alerta" : `${summary.stateAlerts} doenças em alerta`;
  const municipalities =
    summary.municipalityAlerts === 1 ? "1 alerta municipal" : `${summary.municipalityAlerts} alertas municipais`;
  return `${probability} · ${diseases} · ${municipalities}`;
}
