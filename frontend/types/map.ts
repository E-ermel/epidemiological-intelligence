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

export interface MapNode {
  level: MapLevel;
  /** e.g. "RS" when level === "state"; undefined at country level. */
  stateCode?: string;
  label: string;
}
