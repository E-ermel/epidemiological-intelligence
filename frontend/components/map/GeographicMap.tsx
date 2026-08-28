"use client";

import { useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { GeoArea, MapBubble, MapLevel } from "@/types/map";
import { RS_CONTOUR_PATH, RS_CONTOUR_VIEWBOX } from "@/mocks/geography";
import { IBGE_CODAREA_TO_UF } from "@/components/map/ibgeStateCodes";
import { formatNumber } from "@/lib/utils";
import brazilStatesGeoJson from "@/data/geo/brasil-uf.json";

/**
 * Hierarchical map: country -> state -> municipality. Renders one map
 * at a time (never two side by side). The geographic level and which
 * state is selected live in the parent's state, not inside this
 * component -- see components/map/OverviewMap.tsx.
 *
 * Country level renders the real state boundaries (data/geo/brasil-uf.json,
 * from IBGE) as a choropleth. State level (today, only RS) still uses a
 * stylized contour + municipality markers -- see the Fase 2 plan for why
 * municipality-level real polygons weren't pursued.
 */

const COUNTRY_VIEWBOX_WIDTH = 400;
const COUNTRY_VIEWBOX_HEIGHT = 420;

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

  if (level === "country") {
    return (
      <div className="relative">
        <svg
          viewBox={`0 0 ${COUNTRY_VIEWBOX_WIDTH} ${COUNTRY_VIEWBOX_HEIGHT}`}
          className="w-full"
          style={{ maxHeight: 380 }}
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
                      : "Sem dados no momento",
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

  // State level (RS): stylized contour + municipality markers.
  const maxCases = Math.max(1, ...bubbles.filter((b) => b.hasData).map((b) => b.cases));

  function radiusFor(bubble: MapBubble) {
    if (!bubble.hasData) return 3.5;
    const minRadius = 5;
    const maxRadius = 15;
    const ratio = Math.sqrt(bubble.cases / maxCases);
    return minRadius + ratio * (maxRadius - minRadius);
  }

  return (
    <div className="relative">
      <svg
        viewBox={RS_CONTOUR_VIEWBOX}
        className="w-full"
        style={{ maxHeight: 380 }}
        role="img"
        aria-label={`Mapa de ${stateCode}`}
      >
        <path
          d={RS_CONTOUR_PATH}
          fill="var(--color-primary-50)"
          stroke="var(--color-primary-100)"
          strokeWidth={2}
        />

        {bubbles.map((bubble) => {
          const [minX, minY, w, h] = RS_CONTOUR_VIEWBOX.split(" ").map(Number);
          const cx = minX + (bubble.x / 100) * w;
          const cy = minY + (bubble.y / 100) * h;
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
              strokeWidth={1.5}
              className={isClickable ? "cursor-pointer transition-opacity hover:opacity-90" : undefined}
              onMouseEnter={() =>
                setHoveredLabel({
                  name: bubble.name,
                  detail: bubble.hasData ? `${formatNumber(bubble.cases)} casos` : "Sem dados no momento",
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
