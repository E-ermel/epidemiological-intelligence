export type MapLevel = "country" | "state";

/**
 * A municipality marker drawn on top of its state's real boundary.
 * lat/lon are the IBGE centroid (GET /geo/state), projected through the
 * same d3-geo projection as the state polygon itself
 * (components/map/GeographicMap.tsx) at render time.
 */
export interface MapBubble {
  /** 6-digit municipality code. */
  id: string;
  name: string;
  lat: number;
  lon: number;
  cases: number;
  hasData: boolean;
}

/**
 * Mirrors GET /geo/{level}'s response. At country level `id` is the UF
 * code and the polygon (data/geo/brasil-uf.json) supplies the position;
 * at state level `id` is the municipality code and latitude/longitude
 * come with it.
 */
export interface GeoArea {
  id: string;
  name: string;
  cases: number;
  hasData: boolean;
  latitude?: number | null;
  longitude?: number | null;
}

export interface MapNode {
  level: MapLevel;
  /** e.g. "RS" when level === "state"; undefined at country level. */
  stateCode?: string;
  label: string;
}
