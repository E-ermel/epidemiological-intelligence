"""
Ingestão SIDRA/IBGE -> bronze (fonte 🟢 oficial).

Baixa a população por município: uma estimativa anual por arquivo
(populacao_estimada_AAAA.json) e o Censo 2022
(populacao_censo_2022.json), como snapshots em bronze/sidra/. Os anos
vêm da própria API, então uma estimativa nova (o IBGE publica a do ano
em agosto) entra sem mudar código. Arquivo sem mudança não é regravado
(ver ingestion.save_snapshot).

Precisa rodar em southamerica-east1, como as outras ingestões de fontes
do governo.
"""

import json

import requests

from epidemiological_de import config, ingestion

CENSUS_FILE = "populacao_censo_2022.json"


def estimate_file(year: int) -> str:
    return f"populacao_estimada_{year}.json"


def available_years(session: requests.Session) -> list[int]:
    """Anos com estimativa publicada, a partir de SIDRA_FIRST_YEAR."""

    rows = json.loads(ingestion.http_get(config.SIDRA_ESTIMATE_YEARS_URL, session=session).decode("utf-8"))
    years = sorted(int(row["D3C"]) for row in rows[1:])
    return [year for year in years if year >= config.SIDRA_FIRST_YEAR]


def run(session: requests.Session | None = None, root: str | None = None) -> dict[str, str | None]:
    session = session or ingestion.new_session()

    files = {estimate_file(year): config.SIDRA_ESTIMATES_URL.format(year=year) for year in available_years(session)}
    files[CENSUS_FILE] = config.SIDRA_CENSUS_2022_URL

    written: dict[str, str | None] = {}
    for filename, url in files.items():
        written[filename] = ingestion.save_snapshot(
            ingestion.http_get(url, session=session, timeout=300),
            source=config.SIDRA_SOURCE,
            filename=filename,
            url=url,
            source_type="oficial",
            root=root,
        )
        print(f"{filename}: {'sem mudança' if written[filename] is None else 'gravado'}")

    return written


if __name__ == "__main__":
    run()
