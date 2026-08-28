import pandas as pd

from epidemiological_de import config, storage
from epidemiological_de.gold.transform import (
    aggregate_municipality_monthly,
    aggregate_station_monthly,
    join_gold,
    normalize_municipality,
)


def run() -> pd.DataFrame:

    inmet = pd.read_parquet(config.INMET_SILVER_PATH)
    sinan = pd.read_parquet(config.SINAN_SILVER_PATH)

    inmet_gold_base = normalize_municipality(inmet)
    inmet_station_monthly = aggregate_station_monthly(inmet_gold_base)
    inmet_monthly = aggregate_municipality_monthly(inmet_station_monthly)

    duplicates = (
        inmet_monthly
        .groupby(["municipality", "year", "month"])
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

    return gold_df


if __name__ == "__main__":
    run()
