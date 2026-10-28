"use client";

import { useRef, useState } from "react";
import type { GeoArea, MapBubble, MapNode } from "@/types/map";
import type { OverviewFilters } from "@/services/api";
import { GeographicMap } from "@/components/map/GeographicMap";
import { MapBreadcrumb } from "@/components/map/MapBreadcrumb";
import { LoadingState } from "@/components/ui/LoadingState";
import { getMunicipalityBubbles } from "@/services/geographyService";

interface OverviewMapProps {
  countryAreas: GeoArea[];
  /** Same filters as the rest of the page, applied to the state drill-down. */
  filters: OverviewFilters;
  /** Where a municipality/state bubble click sends users to look at data. */
  onNavigateToStudies?: () => void;
}

/**
 * Starts at the country level (all 27 states). Clicking a state with
 * cases loads its municipalities from GET /geo/state -- a state can have
 * hundreds, so they aren't fetched up front. The page remounts this
 * component when the filters change (see app/page.tsx), so a loaded
 * state never shows numbers from older filters.
 */
export function OverviewMap({ countryAreas, filters, onNavigateToStudies }: OverviewMapProps) {
  const [node, setNode] = useState<MapNode>({ level: "country", label: "Brasil" });
  const [bubbles, setBubbles] = useState<MapBubble[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(false);
  // Ignores a slow response for a state the user already left.
  const latestRequest = useRef(0);

  async function openState(area: GeoArea) {
    const request = ++latestRequest.current;
    setNode({ level: "state", stateCode: area.id, label: area.name });
    setBubbles([]);
    setIsLoading(true);
    setError(false);

    try {
      const result = await getMunicipalityBubbles(area.id, filters);
      if (request === latestRequest.current) setBubbles(result);
    } catch {
      if (request === latestRequest.current) setError(true);
    } finally {
      if (request === latestRequest.current) setIsLoading(false);
    }
  }

  function backToCountry() {
    latestRequest.current++;
    setNode({ level: "country", label: "Brasil" });
    setIsLoading(false);
  }

  const breadcrumbPath = node.level === "country" ? ["Brasil"] : ["Brasil", node.label];

  return (
    <div>
      <MapBreadcrumb path={breadcrumbPath} onBack={node.level === "state" ? backToCountry : undefined} />

      {node.level === "country" ? (
        <GeographicMap level="country" countryAreas={countryAreas} onSelectArea={openState} />
      ) : isLoading ? (
        <LoadingState label="Carregando municípios..." />
      ) : error ? (
        <p className="py-8 text-center text-sm text-muted">Não foi possível carregar os municípios.</p>
      ) : (
        <GeographicMap
          level="state"
          stateCode={node.stateCode}
          bubbles={bubbles}
          onSelectBubble={() => onNavigateToStudies?.()}
        />
      )}
    </div>
  );
}
