"""
Tabela de atributos do alerta: uma linha por série × mês-alvo m ×
horizonte h (1-3), com tudo o que se sabe na origem t = m - h.

- casos em t, t-1, t-2 e média dos 3; casos no mesmo mês 1 e 2 anos
  antes do alvo; casos em t sobre o limite do canal em t; surto em t;
- limite, média e desvio do canal do mês-alvo (calculados com anos
  anteriores, conhecidos de antemão);
- clima em t, t-1, t-2 (só o passado: na origem o clima do alvo ainda
  não aconteceu);
- covariáveis, mês do ano do alvo, horizonte, doença e UF.
"""

import numpy as np
import pandas as pd

from common import ALERT_DIR, CLIMATE, COVARIATES, HORIZONS, MIN_CASES, TRAIN_TARGETS

CATEGORICAL = ["disease", "state"]


def load_labels(level: str) -> pd.DataFrame:
    return pd.read_parquet(ALERT_DIR / f"labels_{level}.parquet").sort_values(["series_id", "ds"])


def build(level: str) -> pd.DataFrame:
    labels = load_labels(level)
    grouped = labels.groupby("series_id", sort=False)

    frames = []
    for h in HORIZONS:
        f = pd.DataFrame(
            {
                "series_id": labels["series_id"],
                "disease": labels["disease"],
                "state": labels["state"],
                "ds": labels["ds"],
                "horizon": h,
                "y": labels["y"],
                "outbreak": labels["outbreak"],
                "threshold": labels["threshold"],
                "channel_mean": labels["channel_mean"],
                "channel_sd": labels["channel_sd"],
                "population": labels["population"],
                "target_month": labels["ds"].dt.month,
                "y_same_month_1y": grouped["y"].shift(12),
                "y_same_month_2y": grouped["y"].shift(24),
            }
        )
        for k in range(3):
            f[f"y_origin_l{k}"] = grouped["y"].shift(h + k)
        f["y_origin_mean3"] = f[[f"y_origin_l{k}" for k in range(3)]].mean(axis=1)
        f["origin_over_threshold"] = f["y_origin_l0"] / grouped["threshold"].shift(h).clip(lower=1)
        f["outbreak_origin"] = grouped["outbreak"].shift(h).clip(lower=0)
        f["outbreak_same_month_1y"] = grouped["outbreak"].shift(12).clip(lower=0)  # só p/ o sazonal ingênuo
        for variable in CLIMATE:
            for k in range(3):
                f[f"{variable}_origin_l{k}"] = grouped[variable].shift(h + k)
        for column in COVARIATES:
            f[column] = grouped[column].shift(h)
        frames.append(f)

    table = pd.concat(frames, ignore_index=True)
    table = table[(table["ds"] >= TRAIN_TARGETS[0]) & (table["outbreak"] >= 0)]
    table = table.dropna(subset=["y_origin_l2", "y_same_month_2y"])
    for column in CATEGORICAL:
        table[column] = table[column].astype("category")
    table["min_cases"] = MIN_CASES[level]
    return table.reset_index(drop=True)


FEATURES = (
    ["horizon", "target_month", "threshold", "channel_mean", "channel_sd", "y_same_month_1y", "y_same_month_2y"]
    + [f"y_origin_l{k}" for k in range(3)]
    + ["y_origin_mean3", "origin_over_threshold", "outbreak_origin", "log_population"]
    + [f"{v}_origin_l{k}" for v in CLIMATE for k in range(3)]
    + COVARIATES
    + CATEGORICAL
)


def with_log_population(table: pd.DataFrame) -> pd.DataFrame:
    table["log_population"] = np.log(table["population"])
    return table


def base_variable(feature: str) -> str:
    """Agrupa defasagens numa variável só para a importância."""

    for variable in CLIMATE:
        if feature.startswith(variable):
            return variable
    if feature.startswith("y_origin") or feature == "origin_over_threshold":
        return "recent_cases"
    if feature.startswith("y_same_month"):
        return "same_month_past_years"
    if feature in ("threshold", "channel_mean", "channel_sd"):
        return "endemic_channel"
    return feature
