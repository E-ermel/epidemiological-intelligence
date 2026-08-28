export type MapLevel = "country" | "state";

/**
 * A municipality marker drawn on top of the (real) state-level
 * boundary. Position is a percentage (0-100) within the state
 * contour's viewBox, not a real geographic projection -- see
 * mocks/geography.ts for why. Country-level states no longer use
 * this -- see GeoArea, rendered as real polygons instead.
 */
export interface MapBubble {
  id: string;
  name: string;
  x: number;
  y: number;
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
 * A curated x/y position for a state or municipality -- no case data,
 * since positions come from mocks/geography.ts while case counts come
 * from the real API. See services/geographyService.ts.
 */
export interface GeoPosition {
  id: string;
  name: string;
  x: number;
  y: number;
}

export interface MapNode {
  level: MapLevel;
  /** e.g. "RS" when level === "state"; undefined at country level. */
  stateCode?: string;
  label: string;
}
