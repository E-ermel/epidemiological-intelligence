# Vendored geodata

`brasil-uf.json` -- the 27 Brazilian state (UF) boundaries, GeoJSON.

- **Source**: IBGE's official Malhas Territoriais API v3 (public
  domain / CC0).
  `https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF`
- **Fetched**: 2026-08-28.
- **Quality**: `minima` -- IBGE's own pre-simplified generalization,
  not the full-resolution malha (which is tens of MB). 98.5 KB for
  all 27 states.
- Each feature's `properties` only has `codarea`, IBGE's 2-digit state
  code (e.g. `"43"` for Rio Grande do Sul) -- there's no `nome`/UF
  sigla in the file itself. The lookup from `codarea` to UF sigla is
  in `components/map/ibgeStateCodes.ts` (a small, stable, official
  table -- doesn't need to live in this fetched file).

**Ring winding matters and IBGE's export needs correcting.** `d3-geo`
works in spherical coordinates and needs each polygon's exterior ring
wound clockwise in plain (lon, lat) terms (this is the actual
right-hand rule once you account for the sphere's outward normal --
counterclockwise-in-planar-terms, which is what a naive shoelace check
suggests, is backwards and makes `d3.geoBounds`/`geoPath.bounds()`
silently fall back to the whole globe, `[[-180,-90],[180,90]]`, for
every feature). IBGE's export comes back counterclockwise. Fixed once
here via `@mapbox/geojson-rewind` (devDependency) with `outer: true`:

```js
const rewind = require('@mapbox/geojson-rewind');
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('data/geo/brasil-uf.json', 'utf8'));
rewind(data, true); // true = force exterior rings clockwise (planar)
fs.writeFileSync('data/geo/brasil-uf.json', JSON.stringify(data));
```

To refresh this file: re-run the `curl` above, re-run the rewind step
above, and diff before committing -- IBGE's malha URLs are stable but
not guaranteed to never change, and the winding direction needs
reapplying every time since IBGE always exports counterclockwise.
