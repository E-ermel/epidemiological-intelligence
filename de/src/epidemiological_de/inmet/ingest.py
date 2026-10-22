"""
Ingestão INMET -> bronze (fonte 🟢 oficial).

Baixa o zip anual de dados históricos (todas as estações automáticas
do Brasil) para bronze/inmet/year=AAAA/AAAA.zip. Cada rodada faz um
HEAD por ano e só baixa os que mudaram (ver
ingestion.download_if_changed) -- o INMET revisa anos já "fechados"
(o de 2025 foi alterado em março de 2026), então não basta baixar cada
ano uma vez só.

Precisa rodar em southamerica-east1: o portal não responde fora do
Brasil (ver var.ingest_region no Terraform).
"""

from datetime import datetime, timezone

import requests

from epidemiological_de import config, ingestion


def zip_path(year: int, root: str | None = None) -> str:
    root = (root or config.BRONZE_ROOT).rstrip("/")
    return f"{root}/{config.INMET_SOURCE}/year={year}/{year}.zip"


def years_to_ingest(today: datetime | None = None) -> list[int]:
    current_year = (today or datetime.now(timezone.utc)).year
    return list(range(config.INMET_FIRST_YEAR, current_year + 1))


def run(session: requests.Session | None = None, root: str | None = None) -> dict[int, str | None]:
    session = session or ingestion.new_session()
    written: dict[int, str | None] = {}

    for year in years_to_ingest():
        written[year] = ingestion.download_if_changed(
            config.INMET_YEARLY_ZIP_URL.format(year=year),
            zip_path(year, root),
            source=config.INMET_SOURCE,
            source_type="oficial",
            session=session,
        )

        status = "sem mudança" if written[year] is None else f"baixado em {written[year]}"
        print(f"{year}: {status}")

    return written


if __name__ == "__main__":
    run()
