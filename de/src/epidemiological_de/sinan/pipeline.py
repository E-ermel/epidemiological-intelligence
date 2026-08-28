import pandas as pd

from epidemiological_de import config, storage
from epidemiological_de.sinan import extract, transform


def build_sinan_silver() -> pd.DataFrame:
    disease_dfs = []
    for file_path in extract.list_bronze_files():
        disease_name = extract.match_disease(file_path)
        if disease_name is None:
            print("Arquivo ignorado:", file_path)
            continue

        print("Processando:", disease_name)
        df_raw = extract.read_raw_sinan_csv(file_path)
        df_disease = transform.process_sinan_file(df_raw, disease_name, file_path)
        disease_dfs.append(df_disease)

    if not disease_dfs:
        raise ValueError("Nenhum dataset epidemiológico foi processado.")

    return pd.concat(disease_dfs, ignore_index=True, sort=False)


def print_diagnostics(sinan_silver_df: pd.DataFrame) -> None:
    by_disease = (
        sinan_silver_df.groupby("disease")
        .agg(
            registros=("municipality_code", "size"),
            municipios=("municipality_code", "nunique"),
        )
        .reset_index()
        .sort_values("disease")
    )
    print(by_disease)

    # dropna=False: o groupBy do Spark mantém grupos com year/month nulos.
    duplicate_counts = sinan_silver_df.groupby(
        ["disease", "municipality_code", "year", "month"], dropna=False
    ).size()
    duplicates = duplicate_counts[duplicate_counts > 1]
    print("Duplicatas:", len(duplicates))

    by_disease_year = (
        sinan_silver_df.groupby(["disease", "year"], dropna=False)
        .agg(
            registros=("cases", "size"),
            cases_null=("cases", lambda s: s.isna().sum()),
        )
        .reset_index()
        .sort_values(["disease", "year"])
    )
    print(by_disease_year)


def write_silver(sinan_silver_df: pd.DataFrame) -> None:
    df_out = sinan_silver_df.copy()

    # Coluna de partição não pode ser dtype nullable: o pyarrow grava o Int64 no
    # metadata do pandas e a releitura quebra (dictionary não vira Int64).
    df_out["year"] = df_out["year"].astype("int64")

    # Equivalente a .write.mode("overwrite") do Spark: limpa o prefixo
    # de destino por completo antes de gravar o novo dataset.
    storage.clear_path(config.SINAN_SILVER_PATH)

    df_out.to_parquet(
        config.SINAN_SILVER_PATH,
        engine="pyarrow",
        partition_cols=["disease", "year"],
        index=False,
    )


def verify_silver(sinan_silver_df: pd.DataFrame) -> None:
    sinan_silver_test = pd.read_parquet(config.SINAN_SILVER_PATH, engine="pyarrow")

    original_count = len(sinan_silver_df)
    silver_count = len(sinan_silver_test)

    print("Original:", original_count)
    print("Silver:", silver_count)

    if original_count != silver_count:
        raise ValueError(
            f"SINAN Silver row count mismatch: "
            f"original={original_count}, silver={silver_count}"
        )

    final_stats = (
        sinan_silver_test.groupby("disease")
        .agg(
            records=("cases", "size"),
            total_cases=("cases", "sum"),
            null_cases=("cases", lambda s: s.isna().sum()),
        )
        .reset_index()
        .sort_values("disease")
    )
    print(final_stats)


def run() -> None:
    sinan_silver_df = build_sinan_silver()
    print_diagnostics(sinan_silver_df)
    write_silver(sinan_silver_df)
    verify_silver(sinan_silver_df)


if __name__ == "__main__":
    run()
