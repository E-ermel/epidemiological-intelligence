"""
Leitura do gold nacional para o alerta, em dois quadros:

- cases: doença × município × mês (casos por residência, fonte,
  is_provisional);
- context: município × mês (UF, população e clima; no gold o clima se
  repete em cada doença, aqui vem uma vez só).

Na nuvem lê do BigQuery; localmente (GOLD_PARQUET_DIR) lê o parquet do
gold com a mesma forma.
"""

import pandas as pd

from epidemiological_intelligence.alert import config

CASES_COLUMNS = ["disease", "source", "municipality_code", "state", "ds", "cases", "is_provisional"]
CONTEXT_COLUMNS = ["municipality_code", "state", "ds", "population", *config.CLIMATE]


def _tidy(cases: pd.DataFrame, context: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cases = cases[~cases["disease"].isin(config.EXCLUDED_DISEASES)].copy()
    for column in ("disease", "source", "municipality_code", "state"):
        cases[column] = cases[column].astype(str).astype("category")
    cases["ds"] = pd.to_datetime(cases["ds"]).dt.tz_localize(None).astype("datetime64[ns]")
    cases["cases"] = cases["cases"].astype("float32")
    cases["is_provisional"] = cases["is_provisional"].fillna(False).astype(bool)

    context = context.copy()
    context["municipality_code"] = context["municipality_code"].astype(str)
    context["ds"] = pd.to_datetime(context["ds"]).dt.tz_localize(None).astype("datetime64[ns]")
    for column in ["population", *config.CLIMATE]:
        context[column] = pd.to_numeric(context[column], errors="coerce").astype("float64")
    return cases[CASES_COLUMNS].reset_index(drop=True), context[CONTEXT_COLUMNS].reset_index(drop=True)


def load_from_parquet(gold_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    gold = pd.read_parquet(
        gold_dir,
        columns=["disease", "source", "municipality_code", "state", "reference_date", "cases", "is_provisional",
                 "population", *config.CLIMATE],
    )
    gold["ds"] = gold.pop("reference_date")
    context = gold[CONTEXT_COLUMNS].drop_duplicates(["municipality_code", "ds"])
    return _tidy(gold[CASES_COLUMNS], context)


def load_from_bigquery() -> tuple[pd.DataFrame, pd.DataFrame]:
    from google.cloud import bigquery

    if not config.GCP_PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID não foi definido.")

    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    table = f"`{config.GCP_PROJECT_ID}.{config.BIGQUERY_DATASET}.{config.BIGQUERY_GOLD_TABLE}`"
    climate = ", ".join(f"ANY_VALUE({c}) AS {c}" for c in config.CLIMATE)

    cases = client.query(
        f"""
        SELECT disease, source, municipality_code, state, DATE(reference_date) AS ds, cases, is_provisional
        FROM {table}
        """
    ).to_dataframe()
    context = client.query(
        f"""
        SELECT municipality_code, ANY_VALUE(state) AS state, DATE(reference_date) AS ds,
               ANY_VALUE(population) AS population, {climate}
        FROM {table}
        GROUP BY municipality_code, ds
        """
    ).to_dataframe()
    return _tidy(cases, context)
