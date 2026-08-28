import type { MapBubble } from "@/types/map";

/**
 * MOCK DATA. No endpoint exists for geographic aggregates yet.
 * TODO: backend endpoint required (e.g. GET /geo/{level} returning
 * case counts per state or per municipality).
 *
 * These SVG paths are deliberately simplified, stylized contours --
 * NOT real cartographic boundaries. Per the chosen "bubble map" design
 * (see project decision), the shapes exist only to give visual context;
 * the actual data lives in the bubble positions/sizes, which are
 * approximate percentage coordinates, not a real geographic projection.
 * Swapping in real GeoJSON/TopoJSON boundaries is a possible future
 * upgrade, not required for this first iteration.
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
export const BRAZIL_STATE_BUBBLES: MapBubble[] = [
  { id: "RS", name: "Rio Grande do Sul", x: 46, y: 88, cases: 128_430, hasData: true },
  { id: "SC", name: "Santa Catarina", x: 52, y: 78, cases: 0, hasData: false },
  { id: "PR", name: "Paraná", x: 54, y: 66, cases: 0, hasData: false },
  { id: "SP", name: "São Paulo", x: 58, y: 54, cases: 0, hasData: false },
  { id: "RJ", name: "Rio de Janeiro", x: 68, y: 52, cases: 0, hasData: false },
  { id: "MG", name: "Minas Gerais", x: 62, y: 42, cases: 0, hasData: false },
];

/**
 * Representative Rio Grande do Sul municipalities. Positions are
 * approximate/illustrative (relative placement is roughly right --
 * west/east/north/south -- but not projected from real coordinates).
 */
export const RS_MUNICIPALITY_BUBBLES: MapBubble[] = [
  { id: "porto-alegre", name: "Porto Alegre", x: 62, y: 62, cases: 24_180, hasData: true },
  { id: "caxias-do-sul", name: "Caxias do Sul", x: 66, y: 42, cases: 11_920, hasData: true },
  { id: "pelotas", name: "Pelotas", x: 58, y: 82, cases: 9_540, hasData: true },
  { id: "santa-maria", name: "Santa Maria", x: 42, y: 52, cases: 8_210, hasData: true },
  { id: "canoas", name: "Canoas", x: 63, y: 58, cases: 7_640, hasData: true },
  { id: "novo-hamburgo", name: "Novo Hamburgo", x: 61, y: 50, cases: 6_390, hasData: true },
  { id: "passo-fundo", name: "Passo Fundo", x: 52, y: 28, cases: 5_980, hasData: true },
  { id: "rio-grande", name: "Rio Grande", x: 60, y: 92, cases: 5_120, hasData: true },
  { id: "gravatai", name: "Gravataí", x: 65, y: 56, cases: 4_870, hasData: true },
  { id: "viamao", name: "Viamão", x: 64, y: 63, cases: 4_310, hasData: true },
  { id: "alegrete", name: "Alegrete", x: 22, y: 55, cases: 3_260, hasData: true },
  { id: "uruguaiana", name: "Uruguaiana", x: 12, y: 60, cases: 2_890, hasData: true },
];
