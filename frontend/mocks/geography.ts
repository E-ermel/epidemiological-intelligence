import type { GeoPosition } from "@/types/map";

/**
 * Case counts here are no longer used -- GET /geo/{level} (via
 * services/geographyService.ts) is real now. What's still mock/curated
 * here is the POSITION data for RS municipality markers: x/y percentage
 * coordinates, since there's no real municipality-level projection
 * backing this (see the Fase 2 plan for why the map stays at real
 * state-level polygons, with municipalities as markers rather than
 * their own real polygons). geographyService.ts joins these positions
 * onto the real API data by name; anything the API returns that isn't
 * in this curated list has nowhere to be drawn and is dropped rather
 * than given an invented position.
 *
 * The country-level view no longer uses a stylized contour or curated
 * state positions -- it renders the real state boundaries from
 * data/geo/brasil-uf.json (see components/map/GeographicMap.tsx).
 */

export const RS_CONTOUR_VIEWBOX = "0 0 400 300";
export const RS_CONTOUR_PATH =
  "M40,60 L120,30 L220,25 L300,50 L360,90 L380,140 L350,190 " +
  "L320,230 L260,260 L200,270 L140,250 L90,220 L50,170 L30,110 Z";

/**
 * Rio Grande do Sul municipalities, matched against the 27 that
 * actually have real data in the Gold table today (verified against
 * the live GET /geo/state?state=RS response -- an earlier guess at
 * "the biggest RS cities" only matched 5 of the 27 real ones and
 * silently dropped the rest). Positions are approximate/illustrative
 * (relative placement is roughly right -- west/east/north/south --
 * but not projected from real coordinates). Matching against the API
 * is accent-insensitive (see normalizeMunicipalityName in
 * services/geographyService.ts), so the accented names here are just
 * for readability of this file, not required to match verbatim.
 */
export const RS_MUNICIPALITY_BUBBLES: GeoPosition[] = [
  { id: "porto-alegre", name: "Porto Alegre", x: 62, y: 62 },
  { id: "rio-grande", name: "Rio Grande", x: 60, y: 92 },
  { id: "passo-fundo", name: "Passo Fundo", x: 52, y: 28 },
  { id: "santa-maria", name: "Santa Maria", x: 42, y: 52 },
  { id: "uruguaiana", name: "Uruguaiana", x: 12, y: 60 },
  { id: "bage", name: "Bagé", x: 25, y: 75 },
  { id: "bento-goncalves", name: "Bento Gonçalves", x: 66, y: 38 },
  { id: "cacapava-do-sul", name: "Caçapava do Sul", x: 35, y: 70 },
  { id: "camaqua", name: "Camaquã", x: 52, y: 78 },
  { id: "cambara-do-sul", name: "Cambará do Sul", x: 62, y: 15 },
  { id: "campo-bom", name: "Campo Bom", x: 60, y: 52 },
  { id: "canela", name: "Canela", x: 64, y: 48 },
  { id: "cruz-alta", name: "Cruz Alta", x: 44, y: 32 },
  { id: "erechim", name: "Erechim", x: 56, y: 12 },
  { id: "frederico-westphalen", name: "Frederico Westphalen", x: 50, y: 10 },
  { id: "lagoa-vermelha", name: "Lagoa Vermelha", x: 58, y: 22 },
  { id: "palmeira-das-missoes", name: "Palmeira das Missões", x: 46, y: 22 },
  { id: "rio-pardo", name: "Rio Pardo", x: 48, y: 62 },
  { id: "santa-rosa", name: "Santa Rosa", x: 30, y: 18 },
  { id: "santiago", name: "Santiago", x: 28, y: 45 },
  { id: "santo-augusto", name: "Santo Augusto", x: 32, y: 20 },
  { id: "sao-borja", name: "São Borja", x: 14, y: 45 },
  { id: "soledade", name: "Soledade", x: 48, y: 26 },
  { id: "teutonia", name: "Teutônia", x: 58, y: 44 },
  { id: "torres", name: "Torres", x: 70, y: 20 },
  { id: "tramandai", name: "Tramandaí", x: 66, y: 56 },
  { id: "vacaria", name: "Vacaria", x: 56, y: 10 },
];
