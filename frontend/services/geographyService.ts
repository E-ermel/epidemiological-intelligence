import type { GeoArea, MapBubble } from "@/types/map";
import { getGeo, type OverviewFilters } from "@/services/api";

/**
 * GET /geo/country, straight through: the real polygon
 * (data/geo/brasil-uf.json, rendered by GeographicMap) supplies the
 * position, keyed by IBGE codarea -> sigla (components/map/ibgeStateCodes.ts).
 */
export async function getCountryAreas(filters: OverviewFilters = {}): Promise<GeoArea[]> {
  return getGeo("country", undefined, filters);
}

/**
 * GET /geo/state?state=XX: one marker per municipality, at its IBGE
 * centroid. A municipality without a centroid (created after the last
 * IBGE mesh) has nowhere to be drawn and is dropped.
 */
export async function getMunicipalityBubbles(
  stateCode: string,
  filters: OverviewFilters = {}
): Promise<MapBubble[]> {
  const areas = await getGeo("state", stateCode, filters);

  return areas.flatMap((area) =>
    area.latitude == null || area.longitude == null
      ? []
      : [
          {
            id: area.id,
            name: area.name,
            lat: area.latitude,
            lon: area.longitude,
            cases: area.cases,
            hasData: area.cases > 0,
          },
        ]
  );
}
