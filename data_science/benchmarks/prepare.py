"""
Gold nacional (parquet) -> dataset do benchmark.

Uso: python prepare.py <pasta do gold>

- Uma série por doença × município de residência, de 2015 a dez/2025.
- Clima sem nulos (os modelos com covariáveis não aceitam lacunas):
  falta preenchida pela média do mesmo mês naquele município e, se não
  houver, pela média do mesmo mês e ano na UF.
- Meses de 2025 do SINAN ainda são preliminares (base PRELIM); entram
  assim mesmo, ou peçonhentos e leptospirose ficariam sem teste.
"""

import sys

import pandas as pd

from common import CLIMATE_COLUMNS, DATASET_PATH, LAST_MONTH, OUTPUT_DIR


def fill_climate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    calendar_month = df["ds"].dt.month

    for column in CLIMATE_COLUMNS:
        by_municipality_month = df.groupby(["municipality_code", calendar_month])[column].transform("mean")
        by_state_date = df.groupby(["state", "ds"])[column].transform("mean")
        overall_month = df.groupby(calendar_month)[column].transform("mean")
        df[column] = df[column].fillna(by_municipality_month).fillna(by_state_date).fillna(overall_month)

    return df


def main(gold_dir: str) -> None:
    columns = ["disease", "municipality_code", "state", "reference_date", "cases", *CLIMATE_COLUMNS]
    gold = pd.read_parquet(gold_dir, columns=columns)

    gold["ds"] = pd.to_datetime(gold["reference_date"]).dt.tz_localize(None)
    gold = gold[gold["ds"] <= LAST_MONTH].drop(columns="reference_date")

    # O clima é o mesmo para todas as doenças de um município-mês:
    # preenche numa tabela só e junta de volta.
    climate = gold.drop_duplicates(["municipality_code", "ds"])[["municipality_code", "state", "ds", *CLIMATE_COLUMNS]]
    climate = fill_climate(climate)

    dataset = gold.drop(columns=CLIMATE_COLUMNS).merge(climate, on=["municipality_code", "state", "ds"], how="left")
    dataset = dataset.rename(columns={"cases": "y"})
    dataset["y"] = dataset["y"].astype("float64")
    dataset["unique_id"] = dataset["disease"] + "|" + dataset["municipality_code"]
    dataset = dataset.sort_values(["unique_id", "ds"]).reset_index(drop=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(DATASET_PATH, index=False)

    print(f"{dataset['unique_id'].nunique()} séries, {len(dataset)} linhas, "
          f"{dataset['ds'].min():%Y-%m} a {dataset['ds'].max():%Y-%m}")
    print("Clima nulo após preenchimento:", int(dataset[CLIMATE_COLUMNS].isna().sum().sum()))
    print(dataset.groupby("disease")["y"].sum().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main(sys.argv[1])
