"use client";

import { useState } from "react";
import type { GeoArea, MapBubble, MapNode } from "@/types/map";
import { GeographicMap } from "@/components/map/GeographicMap";
import { MapBreadcrumb } from "@/components/map/MapBreadcrumb";

interface OverviewMapProps {
  countryAreas: GeoArea[];
  stateBubbles: Record<string, MapBubble[]>;
  /** Where a municipality/state bubble click sends users to look at data. */
  onNavigateToStudies?: () => void;
}

const STATE_LABELS: Record<string, string> = {
  RS: "Rio Grande do Sul",
};

/**
 * Starts already drilled into Rio Grande do Sul, since that's where the
 * pipeline currently has data (per project decision). The component
 * itself is generic over level/state -- adding another state only means
 * adding its bubbles + contour, not changing this logic.
 */
export function OverviewMap({ countryAreas, stateBubbles, onNavigateToStudies }: OverviewMapProps) {
  const [node, setNode] = useState<MapNode>({
    level: "state",
    stateCode: "RS",
    label: "Rio Grande do Sul",
  });

  const breadcrumbPath = node.level === "country" ? ["Brasil"] : ["Brasil", node.label];

  return (
    <div>
      <MapBreadcrumb
        path={breadcrumbPath}
        onBack={node.level === "state" ? () => setNode({ level: "country", label: "Brasil" }) : undefined}
      />

      {node.level === "country" ? (
        <GeographicMap
          level="country"
          countryAreas={countryAreas}
          onSelectArea={(area) => {
            const label = STATE_LABELS[area.id];
            if (label) {
              setNode({ level: "state", stateCode: area.id, label });
            }
          }}
        />
      ) : (
        <GeographicMap
          level="state"
          stateCode={node.stateCode}
          bubbles={node.stateCode ? (stateBubbles[node.stateCode] ?? []) : []}
          onSelectBubble={() => onNavigateToStudies?.()}
        />
      )}
    </div>
  );
}
