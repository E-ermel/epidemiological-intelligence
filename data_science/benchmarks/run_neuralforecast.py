"""
PatchTST e TFT (neuralforecast), treinados nos nossos dados.

Uso: python run_neuralforecast.py <patchtst|tft> <nacional|estado>

- nacional: um modelo global com todas as séries do país;
- estado: um modelo por UF, cada um só com as séries dela.

PatchTST usa só o histórico de casos. TFT recebe o clima como
covariável conhecida no futuro (mesmo cenário "clima conhecido" de
chronos2_clima e moirai2_clima) e a UF/doença como estáticas.
"""

import sys
import time

import pandas as pd
from neuralforecast import NeuralForecast
from neuralforecast.losses.pytorch import MAE
from neuralforecast.models import TFT, PatchTST

from common import CLIMATE_COLUMNS, HORIZON, load_dataset, save_predictions, windows

INPUT_SIZE = 36
TRAINER = {"accelerator": "gpu", "devices": 1, "enable_progress_bar": False, "logger": False, "enable_model_summary": False}

STEPS = {"nacional": 2000, "estado": 400}


def build_model(name: str, steps: int):
    common = {
        "h": HORIZON,
        "input_size": INPUT_SIZE,
        "loss": MAE(),
        "max_steps": steps,
        "scaler_type": "robust",
        "batch_size": 256,
        "windows_batch_size": 1024,
        "random_seed": 42,
        **TRAINER,
    }

    if name == "patchtst":
        return PatchTST(**common, patch_len=6, stride=3)
    if name == "tft":
        return TFT(**common, hidden_size=64, futr_exog_list=CLIMATE_COLUMNS)
    raise ValueError(f"Modelo desconhecido: {name}")


def fit_predict(name: str, steps: int, history: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    exog = CLIMATE_COLUMNS if name == "tft" else []

    nf = NeuralForecast(models=[build_model(name, steps)], freq="MS")
    nf.fit(df=history[["unique_id", "ds", "y", *exog]])
    predicted = nf.predict(futr_df=target[["unique_id", "ds", *exog]] if exog else None)

    model_column = [c for c in predicted.columns if c not in ("unique_id", "ds")][0]
    return predicted.reset_index(drop="unique_id" in predicted.columns).rename(columns={model_column: "y_hat"})[
        ["unique_id", "ds", "y_hat"]
    ]


def main(name: str, scope: str) -> None:
    df = load_dataset()
    steps = STEPS[scope]
    predictions = []

    for window, history, target in windows(df):
        groups = [("BR", history, target)] if scope == "nacional" else [
            (state, history[history["state"] == state], target[target["state"] == state])
            for state in sorted(history["state"].unique())
        ]

        for label, group_history, group_target in groups:
            started = time.time()
            predicted = fit_predict(name, steps, group_history, group_target)
            predictions.append(predicted.assign(window=window))
            print(f"{name}/{scope} janela {window} {label}: {group_history['unique_id'].nunique()} séries, "
                  f"{time.time() - started:.0f}s", flush=True)

    save_predictions(pd.concat(predictions, ignore_index=True), f"{name}_{scope}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
