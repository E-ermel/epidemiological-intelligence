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

To refresh this file, re-run the `curl` above and diff before
committing -- IBGE's malha URLs are stable but not guaranteed to never
change.
