"""
Base comum do benchmark de modelos de previsão.

Tarefa: prever os casos mensais de cada série (doença × município de
residência) 12 meses à frente, a partir de duas origens:

- janela 1: histórico até dez/2023, prevê jan-dez/2024;
- janela 2: histórico até dez/2024, prevê jan-dez/2025.

Cada script run_*.py roda um modelo num processo próprio (as libs de
Chronos e Moirai conflitam quando carregadas juntas) e grava as
previsões em OUTPUT_DIR/predictions/<modelo>.parquet, no formato
PREDICTION_COLUMNS. evaluate.py junta tudo e calcula as métricas.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path(os.getenv("BENCHMARK_OUTPUT_DIR", Path(__file__).parent / "output"))
DATASET_PATH = OUTPUT_DIR / "dataset.parquet"
PREDICTIONS_DIR = OUTPUT_DIR / "predictions"

HORIZON = 12
ORIGINS = [pd.Timestamp("2023-12-01"), pd.Timestamp("2024-12-01")]
LAST_MONTH = pd.Timestamp("2025-12-01")

CLIMATE_COLUMNS = [
    "precipitation_sum_mm",
    "temperature_avg_c",
    "dew_point_avg_c",
    "relative_humidity_avg_pct",
    "atmospheric_pressure_avg_mb",
    "wind_speed_avg_ms",
]

SERIES_COLUMNS = ["unique_id", "disease", "municipality_code", "state"]
PREDICTION_COLUMNS = ["unique_id", "ds", "window", "model", "y_hat"]


def load_dataset() -> pd.DataFrame:
    """unique_id, disease, municipality_code, state, ds, y + clima (sem nulos)."""

    return pd.read_parquet(DATASET_PATH)


def windows(df: pd.DataFrame):
    """(número da janela, histórico, alvo) para cada origem."""

    for number, origin in enumerate(ORIGINS, start=1):
        end = origin + pd.DateOffset(months=HORIZON)
        history = df[df["ds"] <= origin]
        target = df[(df["ds"] > origin) & (df["ds"] <= end)]
        yield number, history, target


def save_predictions(predictions: pd.DataFrame, model: str) -> Path:
    predictions = predictions.assign(model=model)
    predictions["y_hat"] = predictions["y_hat"].clip(lower=0).astype("float64")

    missing = set(PREDICTION_COLUMNS) - set(predictions.columns)
    if missing:
        raise ValueError(f"Previsões sem as colunas {missing}")

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = PREDICTIONS_DIR / f"{model}.parquet"
    predictions[PREDICTION_COLUMNS].to_parquet(path, index=False)
    print(f"{model}: {len(predictions)} previsões em {path}")
    return path


def metrics(y: pd.Series, y_hat: pd.Series) -> dict:
    error = (y - y_hat).to_numpy(dtype=float)
    total = float(y.sum())

    return {
        "mae": float(np.abs(error).mean()),
        "rmse": float(np.sqrt((error**2).mean())),
        # Erro absoluto total sobre casos totais: não explode em séries
        # com muitos zeros, como MAPE faria.
        "wape_pct": float(np.abs(error).sum() / total * 100) if total else np.nan,
        "y_total": total,
        "y_hat_total": float(y_hat.sum()),
    }
