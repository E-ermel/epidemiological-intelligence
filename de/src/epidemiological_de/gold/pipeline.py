"""
Silver (SIH, SINAN, INMET, dim_municipality) -> gold nacional (+ BigQuery).

São ~10 milhões de linhas (5.571 municípios × ~140 meses × 13
doenças): o gold é montado e gravado uma doença por vez, em
<GOLD_PATH>/part-NN.parquet, e o BigQuery carrega a pasta direto do
GCS, sem juntar tudo num DataFrame.
"""

import fsspec
import pandas as pd

from epidemiological_de import config, storage, warehouse
from epidemiological_de.gold import transform

# (fonte, silver, coluna de contagem)
SOURCES = [
    ("SIH", config.SIH_SILVER_PATH, "hospitalizations"),
    ("SINAN", config.SINAN_SILVER_PATH, "cases"),
]


def report_unmatched(source: str, counts: pd.DataFrame, dim: pd.DataFrame) -> None:
    """Casos de códigos fora da dim (ignorado, exterior...) não entram no gold."""

    known = set(dim["municipality_code_6"])
    unmatched = counts.loc[~counts["municipality_code"].isin(known), "cases"].sum()
    total = counts["cases"].sum()
    print(f"{source}: {unmatched} de {total} casos ({unmatched / max(total, 1):.2%}) sem município válido de residência")


def report_climate(climate: pd.DataFrame, dim: pd.DataFrame, months: int) -> None:
    by_source = climate["climate_source"].value_counts().to_dict()
    expected = len(dim) * months
    print(f"Clima: {by_source} de {expected} município-meses ({len(climate) / expected:.1%} com clima)")


def run(
    silver_paths: dict[str, str] | None = None,
    gold_path: str | None = None,
    table_id: str | None = None,
) -> int:
    """
    `silver_paths` / `gold_path` / `table_id` sobrescrevem os caminhos
    padrão (teste local). `table_id=""` pula a carga no BigQuery.
    """

    paths = {
        "dim": config.DIM_MUNICIPALITY_SILVER_PATH,
        "station_monthly": config.INMET_STATION_MONTHLY_SILVER_PATH,
        "stations": config.INMET_STATIONS_SILVER_PATH,
        **{source: path for source, path, _ in SOURCES},
        **(silver_paths or {}),
    }
    gold_path = (gold_path or config.GOLD_PATH).rstrip("/")
    table_id = config.GOLD_BIGQUERY_TABLE_ID if table_id is None else table_id

    dim = pd.read_parquet(paths["dim"])
    station_map = pd.read_parquet(paths["stations"])
    station_monthly = pd.read_parquet(paths["station_monthly"])

    duplicated = station_monthly.duplicated(["station_code", "year", "month"]).sum()
    if duplicated:
        raise ValueError(
            f"{duplicated} linhas estação × mês duplicadas no silver do INMET "
            "(zip com duas versões da mesma estação?)"
        )

    climate = transform.municipality_climate(station_monthly, station_map, dim, config.CLIMATE_MAX_DISTANCE_KM)

    storage.clear_path(gold_path)
    total_rows, part = 0, 0

    for source, _, count_column in SOURCES:
        silver = pd.read_parquet(paths[source])
        counts = transform.case_counts(silver, count_column)
        months = transform.month_range(silver, config.GOLD_FIRST_YEAR)
        provisional = transform.provisional_months(silver)

        report_unmatched(source, counts, dim)
        if part == 0:
            report_climate(climate, dim, len(months))

        for disease in sorted(silver["disease"].unique()):
            gold = transform.build_disease_gold(disease, source, counts, months, provisional, dim, climate)

            with fsspec.open(f"{gold_path}/part-{part:02d}.parquet", "wb", auto_mkdir=True) as f:
                gold.to_parquet(f, index=False)

            print(f"{disease} ({source}): {len(gold)} linhas, {gold['cases'].sum()} casos")
            total_rows += len(gold)
            part += 1

    print("Gold:", total_rows, "linhas")

    if table_id:
        loaded = warehouse.load_parquet_uri(f"{gold_path}/*.parquet", table_id, total_rows)
        print("BigQuery:", loaded, "linhas em", table_id)

    return total_rows


if __name__ == "__main__":
    run()
