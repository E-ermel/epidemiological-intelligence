"use client";

import { useMemo, useState } from "react";
import type { MapBubble, MapNode } from "@/types/map";
import { GeographicMap } from "@/components/map/GeographicMap";
import { MapBreadcrumb } from "@/components/map/MapBreadcrumb";

interface OverviewMapProps {
  countryBubbles: MapBubble[];
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
export function OverviewMap({ countryBubbles, stateBubbles, onNavigateToStudies }: OverviewMapProps) {
  const [node, setNode] = useState<MapNode>({
    level: "state",
    stateCode: "RS",
    label: "Rio Grande do Sul",
  });

  const bubbles = useMemo(() => {
    if (node.level === "country") return countryBubbles;
    return node.stateCode ? (stateBubbles[node.stateCode] ?? []) : [];
  }, [node, countryBubbles, stateBubbles]);

  const breadcrumbPath = node.level === "country" ? ["Brasil"] : ["Brasil", node.label];

  return (
    <div>
      <MapBreadcrumb
        path={breadcrumbPath}
        onBack={node.level === "state" ? () => setNode({ level: "country", label: "Brasil" }) : undefined}
      />

      <GeographicMap
        level={node.level}
        stateCode={node.stateCode}
        bubbles={bubbles}
        onSelectBubble={(bubble) => {
          if (node.level === "country") {
            const label = STATE_LABELS[bubble.id];
            if (label) {
              setNode({ level: "state", stateCode: bubble.id, label });
            }
            return;
          }

          onNavigateToStudies?.();
        }}
      />
    </div>
  );
}
