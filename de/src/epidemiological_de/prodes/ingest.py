"""
Ingestão PRODES/INPE -> bronze (fonte 🟢 oficial).

Baixa, para cada bioma, os dois arquivos que o dashboard de
desmatamento do TerraBrasilis usa:
- prodes_<bioma>_data.json: desmatamento (km²) por período PRODES
  (agosto a julho) e recorte (UF, município, UC, terra indígena);
- prodes_<bioma>_loinames.json: nome e código IBGE de cada recorte.

São snapshots pequenos (≤ 4 MB) em bronze/prodes/; arquivo sem mudança
não é regravado (ver ingestion.save_snapshot). O INPE atualiza uma ou
duas vezes por ano (taxa preliminar e consolidada).

Roda em southamerica-east1, como as outras ingestões de fontes do
governo.
"""

import requests

from epidemiological_de import config, ingestion


def data_file(biome: str) -> str:
    return f"prodes_{biome}_data.json"


def loinames_file(biome: str) -> str:
    return f"prodes_{biome}_loinames.json"


def files() -> dict[str, str]:
    """Nome no bronze -> URL, para todos os biomas."""

    base = config.PRODES_DASHBOARD_URL
    urls: dict[str, str] = {}
    for biome in config.PRODES_BIOMES:
        urls[data_file(biome)] = f"{base}/data/prodes_{biome}.json"
        urls[loinames_file(biome)] = f"{base}/config/loinames/prodes_{biome}.json"
    return urls


def run(session: requests.Session | None = None, root: str | None = None) -> dict[str, str | None]:
    session = session or ingestion.new_session()

    written: dict[str, str | None] = {}
    for filename, url in files().items():
        written[filename] = ingestion.save_snapshot(
            ingestion.http_get(url, session=session, timeout=300),
            source=config.PRODES_SOURCE,
            filename=filename,
            url=url,
            source_type="oficial",
            root=root,
        )
        print(f"{filename}: {'sem mudança' if written[filename] is None else 'gravado'}")

    return written


if __name__ == "__main__":
    run()
