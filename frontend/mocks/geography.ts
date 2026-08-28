import type { GeoPosition } from "@/types/map";

/**
 * Case counts here are no longer used -- GET /geo/{level} (via
 * services/geographyService.ts) is real now. What's still mock/curated
 * here is the POSITION data: x/y percentage coordinates for a small,
 * hand-picked set of states/municipalities, since there's no real
 * geographic projection backing this yet (see the Fase 2 plan for
 * replacing the country-level contour with real state boundaries).
 * geographyService.ts joins these positions onto the real API data by
 * id (states) or name (RS municipalities); anything the API returns
 * that isn't in this curated list has nowhere to be drawn and is
 * dropped rather than given an invented position.
 *
 * These SVG paths are deliberately simplified, stylized contours --
 * NOT real cartographic boundaries.
 */

export const BRAZIL_CONTOUR_VIEWBOX = "0 0 400 420";
export const BRAZIL_CONTOUR_PATH =
  "M120,20 L220,15 L280,45 L320,90 L340,140 L330,190 L300,220 " +
  "L310,260 L290,300 L260,330 L230,350 L200,400 L170,360 L150,330 " +
  "L110,320 L90,280 L70,240 L60,190 L50,140 L70,90 L100,50 Z";

export const RS_CONTOUR_VIEWBOX = "0 0 400 300";
export const RS_CONTOUR_PATH =
  "M40,60 L120,30 L220,25 L300,50 L360,90 L380,140 L350,190 " +
  "L320,230 L260,260 L200,270 L140,250 L90,220 L50,170 L30,110 Z";

/**
 * Approximate relative positions of a handful of states, for the
 * country-level view. Only states with real pipeline data are
 * hasData: true; the rest render neutral/disabled, per spec.
 */
export const BRAZIL_STATE_BUBBLES: GeoPosition[] = [
  { id: "RS", name: "Rio Grande do Sul", x: 46, y: 88 },
  { id: "SC", name: "Santa Catarina", x: 52, y: 78 },
  { id: "PR", name: "Paraná", x: 54, y: 66 },
  { id: "SP", name: "São Paulo", x: 58, y: 54 },
  { id: "RJ", name: "Rio de Janeiro", x: 68, y: 52 },
  { id: "MG", name: "Minas Gerais", x: 62, y: 42 },
];

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
