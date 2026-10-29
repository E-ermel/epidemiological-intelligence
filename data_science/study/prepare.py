"""
Gold nacional (parquet) -> painéis do estudo.

Uso: python prepare.py <pasta do gold>

- panel_municipio: doença × município × mês, 2015 a dez/2025, com
  população, clima e covariáveis de ambiente.
- panel_uf: o mesmo somado por UF; clima e covariáveis = média dos
  municípios ponderada pela população.
- Clima sem nulos: falta preenchida pela média do mesmo mês naquele
  município, depois pela média da UF naquele mês (como no benchmark).
  Covariáveis ficam com seus nulos (cada modelo trata).
"""

import sys

import numpy as np
import pandas as pd

from common import CLIMATE, COVARIATES, LAST_MONTH, OUTPUT_DIR, PANEL_PATHS

RAW_COVARIATES = [c for c in COVARIATES if c != "log_population_density"] + ["population_density"]


def fill_climate(context: pd.DataFrame) -> pd.DataFrame:
    calendar_month = context["ds"].dt.month
    for column in CLIMATE:
        by_municipality_month = context.groupby(["municipality_code", calendar_month])[column].transform("mean")
        by_state_date = context.groupby(["state", "ds"])[column].transform("mean")
        overall_month = context.groupby(calendar_month)[column].transform("mean")
        context[column] = context[column].fillna(by_municipality_month).fillna(by_state_date).fillna(overall_month)
    return context


def weighted_mean(df: pd.DataFrame, columns: list[str], keys: list[str]) -> pd.DataFrame:
    """Média ponderada pela população, ignorando nulos coluna a coluna."""

    out = {}
    for column in columns:
        weight = df["population"].where(df[column].notna(), 0.0)
        out[column] = (df[column].fillna(0) * weight).groupby([df[k] for k in keys]).sum() / weight.groupby(
            [df[k] for k in keys]
        ).sum().replace(0, np.nan)
    return pd.DataFrame(out).reset_index()


def main(gold_dir: str) -> None:
    columns = ["disease", "municipality_code", "state", "reference_date", "cases", "population", *RAW_COVARIATES, *CLIMATE]
    gold = pd.read_parquet(gold_dir, columns=columns)
    gold["ds"] = pd.to_datetime(gold["reference_date"]).dt.tz_localize(None)
    gold = gold[gold["ds"] <= LAST_MONTH].drop(columns="reference_date")

    cases = gold[["disease", "municipality_code", "ds", "cases"]].rename(columns={"cases": "y"})
    cases["disease"] = cases["disease"].astype("category")
    cases["y"] = cases["y"].astype("float32")

    context = gold.drop(columns=["disease", "cases"]).drop_duplicates(["municipality_code", "ds"])
    del gold
    context = fill_climate(context)
    context["log_population_density"] = np.log1p(context.pop("population_density"))
    context = context[context["population"].notna()]

    panel = cases.merge(context, on=["municipality_code", "ds"], how="inner")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL_PATHS["municipio"], index=False)
    print(f"municipio: {len(panel)} linhas, {panel['municipality_code'].nunique()} municípios")

    uf_context = weighted_mean(context, [*CLIMATE, *COVARIATES], ["state", "ds"]).merge(
        context.groupby(["state", "ds"], as_index=False)["population"].sum(), on=["state", "ds"]
    )
    uf_cases = panel.groupby(["disease", "state", "ds"], as_index=False, observed=True)["y"].sum()
    uf = uf_cases.merge(uf_context, on=["state", "ds"])
    uf.to_parquet(PANEL_PATHS["uf"], index=False)
    print(f"uf: {len(uf)} linhas")
    print(uf.groupby("disease", observed=True)["y"].sum().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main(sys.argv[1])
