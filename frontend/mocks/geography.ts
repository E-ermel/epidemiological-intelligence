import type { GeoPosition } from "@/types/map";

/**
 * Case counts here are no longer used -- GET /geo/{level} (via
 * services/geographyService.ts) is real now. What's still curated
 * here is the municipality LIST: the real boundary polygon
 * (data/geo/brasil-uf.json) only has state-level detail, not
 * municipalities (see the Fase 2 plan for why real municipality
 * polygons weren't pursued), so there's no authoritative source in
 * this repo for "every RS municipality's coordinates" to draw from.
 * lat/lon below are each municipality's real seat coordinates,
 * though -- not eyeballed placement -- projected through the same
 * d3-geo projection as the real RS polygon at render time
 * (components/map/GeographicMap.tsx), so a marker lands exactly where
 * that municipality actually is.
 *
 * The country-level view no longer uses a stylized contour or curated
 * state positions -- it renders the real state boundaries from
 * data/geo/brasil-uf.json.
 */

export const RS_MAP_VIEWBOX_WIDTH = 460;
export const RS_MAP_VIEWBOX_HEIGHT = 360;

/**
 * Rio Grande do Sul municipalities, matched against the 27 that
 * actually have real data in the Gold table today (verified against
 * the live GET /geo/state?state=RS response -- an earlier guess at
 * "the biggest RS cities" only matched 5 of the 27 real ones and
 * silently dropped the rest). Matching against the API is
 * accent-insensitive (see normalizeMunicipalityName in
 * services/geographyService.ts), so the accented names here are just
 * for readability of this file, not required to match verbatim.
 */
export const RS_MUNICIPALITY_BUBBLES: GeoPosition[] = [
  { id: "porto-alegre", name: "Porto Alegre", lat: -30.0346, lon: -51.2177 },
  { id: "rio-grande", name: "Rio Grande", lat: -32.035, lon: -52.0986 },
  { id: "passo-fundo", name: "Passo Fundo", lat: -28.2624, lon: -52.4092 },
  { id: "santa-maria", name: "Santa Maria", lat: -29.6842, lon: -53.8069 },
  { id: "uruguaiana", name: "Uruguaiana", lat: -29.7547, lon: -57.0883 },
  { id: "bage", name: "Bagé", lat: -31.3314, lon: -54.1069 },
  { id: "bento-goncalves", name: "Bento Gonçalves", lat: -29.1697, lon: -51.5189 },
  { id: "cacapava-do-sul", name: "Caçapava do Sul", lat: -30.5138, lon: -53.4913 },
  { id: "camaqua", name: "Camaquã", lat: -30.8511, lon: -51.8117 },
  { id: "cambara-do-sul", name: "Cambará do Sul", lat: -29.0483, lon: -50.1414 },
  { id: "campo-bom", name: "Campo Bom", lat: -29.6783, lon: -51.0631 },
  { id: "canela", name: "Canela", lat: -29.3572, lon: -50.8106 },
  { id: "cruz-alta", name: "Cruz Alta", lat: -28.6389, lon: -53.6064 },
  { id: "erechim", name: "Erechim", lat: -27.6339, lon: -52.2739 },
  { id: "frederico-westphalen", name: "Frederico Westphalen", lat: -27.3586, lon: -53.3961 },
  { id: "lagoa-vermelha", name: "Lagoa Vermelha", lat: -28.2075, lon: -51.5253 },
  { id: "palmeira-das-missoes", name: "Palmeira das Missões", lat: -27.9022, lon: -53.3142 },
  { id: "rio-pardo", name: "Rio Pardo", lat: -29.9897, lon: -52.3778 },
  { id: "santa-rosa", name: "Santa Rosa", lat: -27.8711, lon: -54.4808 },
  { id: "santiago", name: "Santiago", lat: -29.1911, lon: -54.8692 },
  { id: "santo-augusto", name: "Santo Augusto", lat: -27.8494, lon: -53.7761 },
  { id: "sao-borja", name: "São Borja", lat: -28.6608, lon: -56.0044 },
  { id: "soledade", name: "Soledade", lat: -28.8175, lon: -52.5106 },
  { id: "teutonia", name: "Teutônia", lat: -29.4467, lon: -51.8083 },
  { id: "torres", name: "Torres", lat: -29.335, lon: -49.7269 },
  { id: "tramandai", name: "Tramandaí", lat: -29.985, lon: -50.1336 },
  { id: "vacaria", name: "Vacaria", lat: -28.5122, lon: -50.9339 },
];
