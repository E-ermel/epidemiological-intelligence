import type { GeoArea, MapBubble } from "@/types/map";
import { getGeo, type OverviewFilters } from "@/services/api";
import { RS_MUNICIPALITY_BUBBLES } from "@/mocks/geography";

/**
 * The Gold table stores municipality names with diacritics stripped
 * (e.g. "BENTO GONCALVES"). Normalizing both sides the same way keeps
 * the curated mock names readable (with accents) without depending on
 * matching the API's stripped form verbatim.
 */
function normalizeMunicipalityName(name: string): string {
  return name
    .normalize("NFD")
    .replace(/\p{Mark}/gu, "")
    .toUpperCase();
}

/**
 * GET /geo/country's real case data, straight through -- no position
 * merge needed here. The real polygon (data/geo/brasil-uf.json,
 * rendered by GeographicMap) supplies the position now, keyed by
 * IBGE codarea -> sigla (components/map/ibgeStateCodes.ts), not by a
 * curated x/y like the old bubble map needed.
 */
export async function getCountryAreas(filters: OverviewFilters = {}): Promise<GeoArea[]> {
  return getGeo("country", undefined, filters);
}

/**
 * GET /geo/state?state=RS's real case counts, merged with the curated
 * real lat/lon lookup in mocks/geography.ts -- municipalities are
 * still drawn as markers over the real RS polygon backdrop, not as
 * their own real polygons (see the Fase 2 plan for why). GeographicMap
 * projects lat/lon through the same projection as the polygon at
 * render time. A municipality the API returns that isn't in the
 * curated list has nowhere to be drawn and is dropped, not invented a
 * position for.
 */
export async function getMunicipalityBubbles(
  stateCode: string,
  filters: OverviewFilters = {}
): Promise<MapBubble[]> {
  if (stateCode !== "RS") return [];

  const areas = await getGeo("state", stateCode, filters);

  const positionByName = new Map(
    RS_MUNICIPALITY_BUBBLES.map((b) => [normalizeMunicipalityName(b.name), b])
  );

  return areas.flatMap((area) => {
    const position = positionByName.get(normalizeMunicipalityName(area.name));
    if (!position) return [];

    return [
      {
        id: position.id,
        name: area.name,
        lat: position.lat,
        lon: position.lon,
        cases: area.cases,
        hasData: area.hasData,
      },
    ];
  });
}
