"use client";

import { useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { GeoArea, MapBubble, MapLevel } from "@/types/map";
import { IBGE_CODAREA_TO_UF } from "@/components/map/ibgeStateCodes";
import { formatNumber } from "@/lib/utils";
import brazilStatesGeoJson from "@/data/geo/brasil-uf.json";

/**
 * Hierarchical map: country -> state -> municipality. Renders one map
 * at a time (never two side by side). The geographic level and which
 * state is selected live in the parent's state, not inside this
 * component -- see components/map/OverviewMap.tsx.
 *
 * Both levels render real boundaries from data/geo/brasil-uf.json (IBGE):
 * country level as a 27-state choropleth, state level as the selected
 * state's polygon, refit to the viewBox, as the backdrop for one marker
 * per municipality at its IBGE centroid.
 */

const COUNTRY_VIEWBOX_WIDTH = 460;
const COUNTRY_VIEWBOX_HEIGHT = 480;
const STATE_VIEWBOX_WIDTH = 460;
const STATE_VIEWBOX_HEIGHT = 460;
const MAP_MAX_HEIGHT = 560;

type StateFeature = Feature<Geometry, { codarea: string }>;

const STATES_GEOJSON = brazilStatesGeoJson as unknown as FeatureCollection<
  Geometry,
  { codarea: string }
>;

const STATE_PROJECTION = geoMercator().fitSize(
  [COUNTRY_VIEWBOX_WIDTH, COUNTRY_VIEWBOX_HEIGHT],
  STATES_GEOJSON
);
const STATE_PATH_GENERATOR = geoPath(STATE_PROJECTION);

/** Polygon and projection of one state, fit to the state-level viewBox. */
function stateGeometry(stateCode: string | undefined) {
  const feature = STATES_GEOJSON.features.find(
    (f: StateFeature) => IBGE_CODAREA_TO_UF[f.properties.codarea] === stateCode
  );
  if (!feature) return null;

  const projection = geoMercator().fitSize([STATE_VIEWBOX_WIDTH, STATE_VIEWBOX_HEIGHT], feature);
  return { projection, pathD: geoPath(projection)(feature) ?? undefined };
}

/** Rounded to 2 decimals (thousandths of a pixel, invisible either way):
 * d3-geo's Mercator math goes through Math.tan/Math.log, and Node's
 * V8 vs. the browser's V8 can disagree in the last couple of binary
 * digits -- unrounded, that's a real (if microscopic) SSR/CSR
 * hydration mismatch on every marker. */
function project(projection: ReturnType<typeof geoMercator>, bubble: MapBubble): [number, number] {
  const [x, y] = projection([bubble.lon, bubble.lat]) ?? [0, 0];
  return [Math.round(x * 100) / 100, Math.round(y * 100) / 100];
}

interface GeographicMapProps {
  level: MapLevel;
  stateCode?: string;
  /** Required when level === "country". */
  countryAreas?: GeoArea[];
  /** Required when level === "state" -- municipality markers. */
  bubbles?: MapBubble[];
  onSelectArea?: (area: GeoArea) => void;
  onSelectBubble?: (bubble: MapBubble) => void;
}

export function GeographicMap({
  level,
  stateCode,
  countryAreas = [],
  bubbles = [],
  onSelectArea,
  onSelectBubble,
}: GeographicMapProps) {
  const [hoveredLabel, setHoveredLabel] = useState<{
    name: string;
    detail: string;
    x: number;
    y: number;
  } | null>(null);

  const areaBySigla = useMemo(
    () => new Map(countryAreas.map((area) => [area.id, area])),
    [countryAreas]
  );

  const state = useMemo(() => stateGeometry(stateCode), [stateCode]);

  if (level === "country") {
    return (
      <div className="relative">
        <svg
          viewBox={`0 0 ${COUNTRY_VIEWBOX_WIDTH} ${COUNTRY_VIEWBOX_HEIGHT}`}
          className="w-full"
          style={{ maxHeight: MAP_MAX_HEIGHT }}
          role="img"
          aria-label="Mapa do Brasil"
        >
          {STATES_GEOJSON.features.map((feature: StateFeature) => {
            const sigla = IBGE_CODAREA_TO_UF[feature.properties.codarea];
            const area = sigla ? areaBySigla.get(sigla) : undefined;
            const isClickable = Boolean(area?.hasData && onSelectArea);
            const d = STATE_PATH_GENERATOR(feature) ?? undefined;
            const [cx, cy] = STATE_PATH_GENERATOR.centroid(feature);

            return (
              <path
                key={feature.properties.codarea}
                d={d}
                fill={area?.hasData ? "var(--color-primary-600)" : "var(--color-border-strong)"}
                fillOpacity={area?.hasData ? 0.75 : 0.35}
                stroke="var(--color-surface)"
                strokeWidth={1}
                className={isClickable ? "cursor-pointer transition-opacity hover:opacity-90" : undefined}
                onMouseEnter={() =>
                  setHoveredLabel({
                    name: area?.name ?? sigla ?? feature.properties.codarea,
                    detail: area?.hasData
                      ? `${formatNumber(area.cases)} casos`
                      : "Nenhum caso no período",
                    x: cx,
                    y: cy,
                  })
                }
                onMouseLeave={() =>
                  setHoveredLabel((current) => (current?.name === area?.name ? null : current))
                }
                onClick={() => isClickable && area && onSelectArea?.(area)}
              />
            );
          })}
        </svg>

        {hoveredLabel && (
          <div className="pointer-events-none absolute left-3 top-3 rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-[var(--shadow-card)]">
            <p className="font-medium text-foreground">{hoveredLabel.name}</p>
            <p className="text-muted">{hoveredLabel.detail}</p>
          </div>
        )}
      </div>
    );
  }

  // State level: real polygon backdrop + one marker per municipality.
  if (!state) return null;

  const maxCases = Math.max(1, ...bubbles.filter((b) => b.hasData).map((b) => b.cases));
  // States have up to 853 municipalities (MG): smaller markers than the
  // old 27-municipality RS map, area proportional to cases.
  const minRadius = bubbles.length > 200 ? 1.5 : 3;
  const maxRadius = bubbles.length > 200 ? 9 : 14;

  function radiusFor(bubble: MapBubble) {
    if (!bubble.hasData) return minRadius * 0.7;
    const ratio = Math.sqrt(bubble.cases / maxCases);
    return minRadius + ratio * (maxRadius - minRadius);
  }

  // Bigger markers drawn first, so small ones stay hoverable on top.
  const ordered = [...bubbles].sort((a, b) => b.cases - a.cases);

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${STATE_VIEWBOX_WIDTH} ${STATE_VIEWBOX_HEIGHT}`}
        className="w-full"
        style={{ maxHeight: MAP_MAX_HEIGHT }}
        role="img"
        aria-label={`Mapa de ${stateCode}`}
      >
        <path
          d={state.pathD}
          fill="var(--color-primary-50)"
          stroke="var(--color-primary-100)"
          strokeWidth={2}
        />

        {ordered.map((bubble) => {
          const [cx, cy] = project(state.projection, bubble);
          const isClickable = bubble.hasData && Boolean(onSelectBubble);

          return (
            <circle
              key={bubble.id}
              cx={cx}
              cy={cy}
              r={radiusFor(bubble)}
              fill={bubble.hasData ? "var(--color-primary-600)" : "var(--color-border-strong)"}
              fillOpacity={bubble.hasData ? 0.75 : 0.5}
              stroke="var(--color-surface)"
              strokeWidth={bubbles.length > 200 ? 0.75 : 1.5}
              className={isClickable ? "cursor-pointer transition-opacity hover:opacity-90" : undefined}
              onMouseEnter={() =>
                setHoveredLabel({
                  name: bubble.name,
                  detail: bubble.hasData ? `${formatNumber(bubble.cases)} casos` : "Nenhum caso no período",
                  x: cx,
                  y: cy,
                })
              }
              onMouseLeave={() =>
                setHoveredLabel((current) => (current?.name === bubble.name ? null : current))
              }
              onClick={() => isClickable && onSelectBubble?.(bubble)}
            />
          );
        })}
      </svg>

      {hoveredLabel && (
        <div className="pointer-events-none absolute left-3 top-3 rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-[var(--shadow-card)]">
          <p className="font-medium text-foreground">{hoveredLabel.name}</p>
          <p className="text-muted">{hoveredLabel.detail}</p>
        </div>
      )}
    </div>
  );
}
