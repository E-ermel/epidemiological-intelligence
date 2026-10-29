"""
Ingestão SNIS (saneamento) -> bronze (🟢 Ministério das Cidades, pela
cópia 🔵 da Base dos Dados).

Uma linha por município × ano de referência, só com os indicadores que
o projeto usa (ver INDICATORS). O resultado vai para bronze/snis/ como
CSV; mudar os indicadores é mudar INDICATORS e reingerir.
"""

from google.cloud import bigquery

from epidemiological_de import config, ingestion

FILENAME = "snis_municipio_agua_esgoto.csv"

# coluna da Base dos Dados (código SNIS) -> nome no silver/gold. O
# atendimento urbano de água (IN023) ficou de fora: a cópia não o tem em
# 2022 e o atendimento total (IN055) cobre o mesmo.
INDICATORS = {
    "indice_atendimento_total_agua": "water_coverage_pct",  # IN055
    "indice_atendimento_esgoto_agua": "sewage_coverage_pct",  # IN056
    "indice_esgotamento_agua_consumida": "sewage_treated_pct",  # IN046
    "indice_perda_distribuicao_agua": "water_loss_distribution_pct",  # IN049
    "indice_perda_ligacao_agua": "water_loss_per_connection",  # IN051, L/dia/ligação
    "indice_perda_faturamento": "water_loss_billing_pct",  # IN013
    "indice_consumo_agua_per_capita": "water_per_capita",  # IN022, L/hab/dia
}


def query() -> str:
    return f"""
        SELECT ano, id_municipio, {', '.join(INDICATORS)}
        FROM `{config.SNIS_BIGQUERY_TABLE}`
        WHERE ano >= {int(config.SNIS_FIRST_YEAR) - int(config.SNIS_MAX_CARRY_YEARS)}
        ORDER BY ano, id_municipio
    """


def run(client: bigquery.Client | None = None, root: str | None = None) -> str | None:
    return ingestion.bigquery_snapshot(
        client or bigquery.Client(project=config.GCP_PROJECT_ID),
        query(),
        table=config.SNIS_BIGQUERY_TABLE,
        source=config.SNIS_SOURCE,
        filename=FILENAME,
        root=root,
    )


if __name__ == "__main__":
    run()
