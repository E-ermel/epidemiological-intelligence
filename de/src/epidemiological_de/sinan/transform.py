from datetime import datetime, timezone

import pandas as pd


MONTH_MAP = {
    "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12,
}

SILVER_COLUMNS = [
    "municipality_code", "municipality", "year", "month",
    "reference_date", "cases", "disease", "source_file", "ingestion_timestamp",
]


def _parse_cases(valor: object) -> object:
    if pd.isna(valor):
        return pd.NA

    trimmed = str(valor).strip()
    if trimmed == "SEM":
        return pd.NA
    if trimmed == "-":
        return 0
    try:
        return int(trimmed)
    except ValueError:
        # mirrors try_cast: invalid numeric strings become null, not an error
        return pd.NA


def process_sinan_file(
    df: pd.DataFrame,
    disease_name: str,
    source_file: str,
) -> pd.DataFrame:

    df = df.copy()

    municipality_column = df.columns[0]
    month_columns = [c for c in df.columns if c != municipality_column]

    df_long = df.rename(columns={municipality_column: "municipio"}).melt(
        id_vars="municipio",
        value_vars=month_columns,
        var_name="ano_mes",
        value_name="valor",
    )

    # reindex garante as duas colunas: Spark getItem(1) devolve null quando o
    # header não tem "/", enquanto o expand do pandas devolveria só a coluna 0.
    ano_mes_split = (
        df_long["ano_mes"]
        .astype("string")
        .str.split("/", n=1, expand=True)
        .reindex(columns=[0, 1])
    )
    df_long["year"] = pd.to_numeric(ano_mes_split[0], errors="coerce").astype("Int64")
    df_long["month_name"] = ano_mes_split[1]
    df_long["month"] = df_long["month_name"].map(MONTH_MAP).astype("Int64")

    df_long["cases"] = df_long["valor"].apply(_parse_cases).astype("Int64")

    # regexp_extract do Spark devolve string vazia quando não casa, não null.
    df_long["municipality_code"] = (
        df_long["municipio"].str.extract(r"^(\d+)", expand=False).fillna("")
    )
    df_long["municipality"] = (
        df_long["municipio"]
        .str.replace(r"^\d+\s*", "", regex=True)
        .str.strip()
        .str.upper()
    )

    year_str = df_long["year"].astype("string")
    month_str = df_long["month"].astype("string").str.zfill(2)
    df_long["reference_date"] = pd.to_datetime(
        year_str + "-" + month_str + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )

    df_long["disease"] = disease_name
    df_long["source_file"] = source_file
    df_long["ingestion_timestamp"] = datetime.now(timezone.utc)

    return df_long[SILVER_COLUMNS]
