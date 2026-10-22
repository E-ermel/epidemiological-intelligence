"""
Ingestão IBGE -> bronze (fonte 🟢 oficial).

Baixa a lista de municípios e os metadados da malha municipal
(centróide e área) e grava cada um como snapshot em bronze/ibge/.
Rodar de novo sem mudança no IBGE não grava nada (ver ingestion.py).
"""

import requests

from epidemiological_de import config, ingestion

MUNICIPIOS_FILE = "municipios.json"
MALHA_METADADOS_FILE = "malha_municipios_metadados.json"

FILES = {
    MUNICIPIOS_FILE: config.IBGE_MUNICIPIOS_URL,
    MALHA_METADADOS_FILE: config.IBGE_MALHA_METADADOS_URL,
}


def run(session: requests.Session | None = None, root: str | None = None) -> dict[str, str | None]:
    session = session or requests.Session()
    written: dict[str, str | None] = {}

    for filename, url in FILES.items():
        content = ingestion.http_get(url, session=session)

        written[filename] = ingestion.save_snapshot(
            content,
            source=config.IBGE_SOURCE,
            filename=filename,
            url=url,
            source_type="oficial",
            root=root,
        )

        if written[filename] is None:
            print(f"{filename}: sem mudança desde a última ingestão")
        else:
            print(f"{filename}: gravado em {written[filename]}")

    return written


if __name__ == "__main__":
    run()
