"""
Ingestão MapBiomas -> bronze (🟠 MapBiomas, pela cópia 🔵 da Base dos Dados).

A tabela tem uma linha por município × ano × classe de cobertura
(~3,4 milhões de linhas desde 2015). A consulta já soma a área (ha) por
grupo de classes, no recorte que o projeto usa; o bronze guarda esse
resultado (~5.600 municípios × ano) como CSV. Mudar os grupos é mudar
GROUPS e reingerir.
"""

from google.cloud import bigquery

from epidemiological_de import config, ingestion

FILENAME = "cobertura_municipio_grupos.csv"

# coluna -> condição sobre a legenda do MapBiomas (níveis 1 e 2).
GROUPS = {
    "area_forest": "nivel_1 = 'Floresta'",
    "area_natural_non_forest": "nivel_1 = 'Vegetação Herbácea e Arbustiva'",
    "area_farming": "nivel_1 = 'Agropecuária'",
    "area_pasture": "nivel_2 = 'Pastagem'",
    "area_agriculture": "nivel_2 = 'Agricultura'",
    "area_urban": "nivel_2 = 'Área Urbanizada'",
    "area_water": "nivel_1 = \"Corpo d'Água\"",
}


def query() -> str:
    sums = ",\n            ".join(f"SUM(IF({condition}, area, 0)) AS {column}" for column, condition in GROUPS.items())
    return f"""
        SELECT
            ano,
            id_municipio,
            SUM(area) AS area_total,
            {sums}
        FROM `{config.MAPBIOMAS_BIGQUERY_TABLE}`
        WHERE ano >= {int(config.MAPBIOMAS_FIRST_YEAR)}
        GROUP BY ano, id_municipio
        ORDER BY ano, id_municipio
    """


def run(client: bigquery.Client | None = None, root: str | None = None) -> str | None:
    return ingestion.bigquery_snapshot(
        client or bigquery.Client(project=config.GCP_PROJECT_ID),
        query(),
        table=config.MAPBIOMAS_BIGQUERY_TABLE,
        source=config.MAPBIOMAS_SOURCE,
        filename=FILENAME,
        root=root,
    )


if __name__ == "__main__":
    run()
