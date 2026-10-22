import pandas as pd

from epidemiological_de import config, storage, warehouse
from epidemiological_de.gold.transform import (
    aggregate_municipality_monthly,
    attach_municipality,
    join_gold,
)


def run() -> pd.DataFrame:

    # Agregado estação × mês e mapa estação -> município, ambos gerados
    # pelo pipeline do INMET -- o silver horário (Brasil todo) não é
    # carregado aqui.
    station_monthly = pd.read_parquet(config.INMET_STATION_MONTHLY_SILVER_PATH)
    station_map = pd.read_parquet(config.INMET_STATIONS_SILVER_PATH)
    sinan = pd.read_parquet(config.SINAN_SILVER_PATH)

    inmet_monthly = aggregate_municipality_monthly(
        attach_municipality(station_monthly, station_map)
    )

    duplicates = (
        inmet_monthly
        .groupby(["municipality_code", "year", "month"])
        .size()
        .loc[lambda counts: counts > 1]
    )
    print("Duplicatas:", len(duplicates))

    gold_df = join_gold(sinan, inmet_monthly)

    print("SINAN:", len(sinan))
    print("GOLD:", len(gold_df))
    print("Sem clima:", gold_df["precipitation_sum_mm"].isna().sum())

    # O join é um LEFT JOIN do SINAN com uma linha climática única por
    # município/ano/mês, então a contagem de linhas não pode mudar.
    if len(gold_df) != len(sinan):
        raise ValueError(
            f"Gold join changed row count: "
            f"SINAN={len(sinan)}, GOLD={len(gold_df)}"
        )

    duplicates_after_join = (
        gold_df
        .groupby(["disease", "municipality", "year", "month"])
        .size()
        .loc[lambda counts: counts > 1]
    )
    print("Duplicatas após join:", len(duplicates_after_join))

    if len(duplicates_after_join) > 0:
        raise ValueError(
            f"Gold contains {len(duplicates_after_join)} duplicate keys after join."
        )

    # Equivalente a .write.mode("overwrite") do Spark: limpa o prefixo
    # de destino por completo antes de gravar o novo dataset.
    storage.clear_path(config.GOLD_PATH)

    # GOLD_PATH é um prefixo de diretório (como a escrita do Spark, que gera
    # múltiplos arquivos part-*); to_parquet precisa de um nome de arquivo.
    gold_df.to_parquet(f"{config.GOLD_PATH}part-0.parquet")

    gold_test = pd.read_parquet(config.GOLD_PATH)
    print(gold_test.dtypes)

    original_count = len(gold_df)
    stored_count = len(gold_test)

    print("Original Gold:", original_count)
    print("Stored Gold:", stored_count)

    if original_count != stored_count:
        raise ValueError(
            f"Gold row count mismatch: "
            f"original={original_count}, stored={stored_count}"
        )

    loaded_rows = warehouse.load_dataframe(gold_df, config.GOLD_BIGQUERY_TABLE_ID)
    print("BigQuery:", loaded_rows, "linhas em", config.GOLD_BIGQUERY_TABLE_ID)

    return gold_df


if __name__ == "__main__":
    run()
