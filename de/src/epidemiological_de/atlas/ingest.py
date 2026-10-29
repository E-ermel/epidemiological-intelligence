"""
Ingestão Atlas Brasil (IDHM) -> bronze (fonte 🔵 espelho).

O Atlas do Desenvolvimento Humano (🟡 PNUD/IPEA/FJP) não tem download
automatizável. A Base dos Dados mantém uma cópia pública no BigQuery:
a consulta roda no projeto (custo de poucos MB) e o resultado vai para
bronze/atlas/ como CSV, com manifesto marcado como espelho.

Os dados são dos censos de 1991, 2000 e 2010 -- estáticos; um snapshot
novo só é gravado se a cópia mudar.
"""

from google.cloud import bigquery

from epidemiological_de import config, ingestion

FILENAME = "atlas_municipio.csv"

# Colunas da tabela da Base dos Dados (ver atlas/transform.py).
COLUMNS = [
    "ano",
    "id_municipio",
    "idhm",
    "idhm_e",
    "idhm_l",
    "idhm_r",
    "indice_gini",
    "renda_pc",
    "expectativa_vida",
    "mortalidade_1",
    "taxa_agua_encanada",
    "taxa_banheiro_agua_encanada",
    "taxa_coleta_lixo",
    "taxa_agua_esgoto_inadequados",
    "populacao_urbana",
    "populacao_rural",
]


def query() -> str:
    return f"SELECT {', '.join(COLUMNS)} FROM `{config.ATLAS_BIGQUERY_TABLE}` ORDER BY ano, id_municipio"


def run(client: bigquery.Client | None = None, root: str | None = None) -> str | None:
    return ingestion.bigquery_snapshot(
        client or bigquery.Client(project=config.GCP_PROJECT_ID),
        query(),
        table=config.ATLAS_BIGQUERY_TABLE,
        source=config.ATLAS_SOURCE,
        filename=FILENAME,
        root=root,
    )


if __name__ == "__main__":
    run()
