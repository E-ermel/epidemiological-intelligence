import type { MapBubble, MapLevel } from "@/types/map";
import { BRAZIL_STATE_BUBBLES, RS_MUNICIPALITY_BUBBLES } from "@/mocks/geography";

/**
 * TODO: backend endpoint required (e.g. GET /geo/{level}?state={code}).
 * See mocks/geography.ts for why the coordinates are approximate.
 */
export async function getMapBubbles(level: MapLevel, stateCode?: string): Promise<MapBubble[]> {
  if (level === "country") {
    return BRAZIL_STATE_BUBBLES;
  }

  if (stateCode === "RS") {
    return RS_MUNICIPALITY_BUBBLES;
  }

  return [];
}
