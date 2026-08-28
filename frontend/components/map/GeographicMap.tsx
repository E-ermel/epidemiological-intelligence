"use client";

import { useMemo, useState } from "react";
import type { MapBubble, MapLevel } from "@/types/map";
import {
  BRAZIL_CONTOUR_PATH,
  BRAZIL_CONTOUR_VIEWBOX,
  RS_CONTOUR_PATH,
  RS_CONTOUR_VIEWBOX,
} from "@/mocks/geography";
import { formatNumber } from "@/lib/utils";

/**
 * Hierarchical map: country -> state -> municipality. Renders one map at
 * a time (never two side by side). The geographic level and which state
 * is selected live in the parent's state, not inside this component --
 * see app/page.tsx for the country/state toggle. Today only RS has a
 * contour + bubbles; other states render as neutral, non-clickable dots
 * at the country level until they have real data.
 */

const CONTOURS: Record<string, { viewBox: string; path: string }> = {
  country: { viewBox: BRAZIL_CONTOUR_VIEWBOX, path: BRAZIL_CONTOUR_PATH },
  RS: { viewBox: RS_CONTOUR_VIEWBOX, path: RS_CONTOUR_PATH },
};

interface GeographicMapProps {
  level: MapLevel;
  stateCode?: string;
  bubbles: MapBubble[];
  onSelectBubble?: (bubble: MapBubble) => void;
}

export function GeographicMap({ level, stateCode, bubbles, onSelectBubble }: GeographicMapProps) {
  const [hovered, setHovered] = useState<MapBubble | null>(null);

  const contour = level === "state" && stateCode ? CONTOURS[stateCode] : CONTOURS.country;

  const maxCases = useMemo(
    () => Math.max(1, ...bubbles.filter((b) => b.hasData).map((b) => b.cases)),
    [bubbles]
  );

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
        viewBox={contour?.viewBox ?? BRAZIL_CONTOUR_VIEWBOX}
        className="w-full"
        style={{ maxHeight: 380 }}
        role="img"
        aria-label={level === "country" ? "Mapa do Brasil" : `Mapa de ${stateCode}`}
      >
        {contour && (
          <path
            d={contour.path}
            fill="var(--color-primary-50)"
            stroke="var(--color-primary-100)"
            strokeWidth={2}
          />
        )}

        {bubbles.map((bubble) => {
          const [minX, minY, w, h] = (contour?.viewBox ?? BRAZIL_CONTOUR_VIEWBOX)
            .split(" ")
            .map(Number);
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
              onMouseEnter={() => setHovered(bubble)}
              onMouseLeave={() => setHovered((current) => (current?.id === bubble.id ? null : current))}
              onClick={() => isClickable && onSelectBubble?.(bubble)}
            />
          );
        })}
      </svg>

      {hovered && (
        <div className="pointer-events-none absolute left-3 top-3 rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-[var(--shadow-card)]">
          <p className="font-medium text-foreground">{hovered.name}</p>
          <p className="text-muted">
            {hovered.hasData ? `${formatNumber(hovered.cases)} casos` : "Sem dados no momento"}
          </p>
        </div>
      )}
    </div>
  );
}
