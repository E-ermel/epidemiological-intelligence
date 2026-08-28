import pandas as pd

from epidemiological_de import config
from epidemiological_de.inmet import extract, transform


def parse_inmet_file(file_path: str) -> pd.DataFrame:
    lines = extract.read_raw_lines(file_path)
    metadata = extract.extract_metadata(lines)
    return transform.build_silver_dataframe(lines, metadata, file_path)


def build_inmet_silver(files: list) -> pd.DataFrame:
    all_dfs = [parse_inmet_file(file_path) for file_path in files]

    if not all_dfs:
        raise ValueError("Nenhum arquivo CSV do INMET foi encontrado.")

    print("DataFrames processados:", len(all_dfs))

    inmet_silver_df = pd.concat(all_dfs, ignore_index=True, sort=False)
    return transform.standardize_inmet_silver(inmet_silver_df)


def print_quality_report(df: pd.DataFrame) -> None:
    print("Total de registros:", len(df))
    print("Timestamps nulos:", df["timestamp"].isna().sum())
    print("Municipality nulos:", df["municipality"].isna().sum())
    print("Station name nulos:", df["station_name"].isna().sum())
    print("Station code nulos:", df["station_code"].isna().sum())
    print("Precipitações negativas:", (df["precipitation_mm"] < 0).sum())

    # dropna=False para contar grupos com chave nula, como o groupBy do Spark.
    group_sizes = df.groupby(["station_code", "timestamp"], dropna=False).size()
    duplicates = (group_sizes > 1).sum()
    print("Duplicatas station_code + timestamp:", duplicates)


def run_pipeline() -> None:
    files = extract.list_csv_files(config.INMET_BRONZE_PATH)
    print("Arquivos CSV encontrados:", len(files))

    inmet_silver_df = build_inmet_silver(files)

    print_quality_report(inmet_silver_df)

    inmet_silver_df.to_parquet(
        config.INMET_SILVER_PATH,
        engine="pyarrow",
        partition_cols=["year"],
        index=False,
        existing_data_behavior="delete_matching",
    )

    silver_test = pd.read_parquet(config.INMET_SILVER_PATH, engine="pyarrow")

    original_count = len(inmet_silver_df)
    silver_count = len(silver_test)
    print("Original:", original_count)
    print("Silver:", silver_count)

    if original_count != silver_count:
        raise ValueError(
            f"Contagem divergente: original={original_count}, silver={silver_count}"
        )


if __name__ == "__main__":
    run_pipeline()
