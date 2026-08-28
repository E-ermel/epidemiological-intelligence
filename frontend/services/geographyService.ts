import type { MapBubble, MapLevel } from "@/types/map";
import { getGeo } from "@/services/api";
import { BRAZIL_STATE_BUBBLES, RS_MUNICIPALITY_BUBBLES } from "@/mocks/geography";

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
 * GET /geo/{level} returns real case counts ({id, name, cases, hasData})
 * but no x/y -- the API has no business knowing pixel positions. This
 * merges that real data with the curated position lookup in
 * mocks/geography.ts (still real municipality names/state codes, just
 * hand-placed positions -- see that file's docstring). A municipality
 * the API returns that isn't in the curated list has nowhere to be
 * drawn and is dropped, not invented a position for.
 */
export async function getMapBubbles(level: MapLevel, stateCode?: string): Promise<MapBubble[]> {
  const areas = await getGeo(level, stateCode);

  if (level === "country") {
    const positionById = new Map(BRAZIL_STATE_BUBBLES.map((b) => [b.id, b]));

    return areas.flatMap((area) => {
      const position = positionById.get(area.id);
      if (!position) return [];

      return [
        {
          id: area.id,
          name: area.name,
          x: position.x,
          y: position.y,
          cases: area.cases,
          hasData: area.hasData,
        },
      ];
    });
  }

  if (stateCode === "RS") {
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
          x: position.x,
          y: position.y,
          cases: area.cases,
          hasData: area.hasData,
        },
      ];
    });
  }

  return [];
}
