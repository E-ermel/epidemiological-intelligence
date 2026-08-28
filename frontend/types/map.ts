export type MapLevel = "country" | "state";

/**
 * A municipality marker drawn on top of the (real) state-level
 * boundary. lat/lon are real coordinates (see GeoPosition), projected
 * through the same d3-geo projection as the boundary polygon itself
 * (components/map/GeographicMap.tsx) at render time -- not a
 * percentage-of-viewBox guess. Country-level states no longer use
 * this -- see GeoArea, rendered as real polygons instead.
 */
export interface MapBubble {
  id: string;
  name: string;
  lat: number;
  lon: number;
  cases: number;
  hasData: boolean;
}

/**
 * A state or municipality's case data with no position -- used at
 * country level, where the real polygon (data/geo/brasil-uf.json)
 * supplies the position instead of a curated x/y. Mirrors
 * GET /geo/{level}'s response exactly.
 */
export interface GeoArea {
  id: string;
  name: string;
  cases: number;
  hasData: boolean;
}

/**
 * A curated real lat/lon for a municipality -- no case data, since
 * positions come from mocks/geography.ts while case counts come from
 * the real API. See services/geographyService.ts. Projected through
 * the same d3-geo projection as the real RS polygon
 * (components/map/GeographicMap.tsx), so a marker lands exactly where
 * that municipality actually is on the real boundary, not an
 * eyeballed percentage.
 */
export interface GeoPosition {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

export interface MapNode {
  level: MapLevel;
  /** e.g. "RS" when level === "state"; undefined at country level. */
  stateCode?: string;
  label: string;
}
