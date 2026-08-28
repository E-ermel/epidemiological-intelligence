export type MapLevel = "country" | "state";

/**
 * A single point rendered on the map: a state (country level) or a
 * municipality (state level). Position is a percentage (0-100) within the
 * simplified contour's viewBox, not a real geographic projection -- see
 * mocks/geography.ts for why.
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
