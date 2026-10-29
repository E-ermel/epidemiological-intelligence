"""
Parte B, PatchTST e TFT (neuralforecast) no alerta. Diferente dos
modelos de fundação, estes são treinados nos nossos dados: um modelo
global por nível, treinado uma vez com o histórico até dez/2022 (último
alvo de treino) e depois aplicado em cada origem mensal (dez/2022 a
nov/2025) sem retreino. A perda é quantílica (MQLoss) e a probabilidade
de surto sai dos quantis, como em alert_foundation.py.

Uso: python alert_neural.py <patchtst|tft> [--steps N]

PatchTST usa só os casos. TFT recebe o clima passado (hist_exog: na
origem o clima dos meses previstos ainda não é conhecido), a mesma
informação de chronos2_clima.
"""

import argparse
import time

import numpy as np
import pandas as pd
from neuralforecast import NeuralForecast
from neuralforecast.losses.pytorch import MQLoss
from neuralforecast.models import TFT, PatchTST

from alert_features import load_labels
from alert_foundation import CHRONOS_LEVELS, H, ORIGINS
from common import CLIMATE, HORIZONS, MIN_CASES, TEST_TARGETS, TRAIN_TARGETS, exceed_probability, save_alert

INPUT_SIZE = 36
STEPS = 2000
TRAINER = {"accelerator": "gpu", "devices": 1, "enable_progress_bar": False, "logger": False, "enable_model_summary": False}


def build_model(name: str, steps: int):
    common = {
        "h": H,
        "input_size": INPUT_SIZE,
        "loss": MQLoss(quantiles=list(CHRONOS_LEVELS)),
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
        return TFT(**common, hidden_size=64, hist_exog_list=CLIMATE)
    raise ValueError(f"Modelo desconhecido: {name}")


def frame(labels: pd.DataFrame, exog: list[str]) -> pd.DataFrame:
    df = labels[["series_id", "ds", "y", *exog]].rename(columns={"series_id": "unique_id"})
    if exog:  # buracos de estação: repete o último valor, depois a mediana da série
        grouped = df.groupby("unique_id")[exog]
        df[exog] = grouped.ffill()
        df[exog] = df[exog].fillna(df.groupby("unique_id")[exog].transform("median")).fillna(df[exog].median())
    return df


def quantile_columns(predicted: pd.DataFrame) -> list[str]:
    """Colunas dos quantis na ordem de CHRONOS_LEVELS (a mediana vem sem sufixo de nível)."""

    columns = [c for c in predicted.columns if c not in ("unique_id", "ds")]
    if len(columns) != len(CHRONOS_LEVELS):
        raise ValueError(f"Esperava {len(CHRONOS_LEVELS)} quantis, vieram {columns}")
    return columns


def run_level(name: str, level: str, steps: int) -> pd.DataFrame:
    labels = load_labels(level)
    exog = CLIMATE if name == "tft" else []
    df = frame(labels, exog)
    targets = labels.set_index(["series_id", "ds"])[["threshold", "outbreak", "disease", "state"]]

    start = time.time()
    nf = NeuralForecast(models=[build_model(name, steps)], freq="MS")
    nf.fit(df=df[df["ds"] <= TRAIN_TARGETS[1]])
    print(f"{name} {level}: treino {time.time() - start:.0f}s", flush=True)

    frames = []
    for origin in ORIGINS:
        predicted = nf.predict(df=df[df["ds"] <= origin]).reset_index()
        predicted = predicted.drop(columns=[c for c in ("index",) if c in predicted.columns])
        columns = quantile_columns(predicted)
        predicted = predicted.sort_values(["unique_id", "ds"])
        ids = predicted["unique_id"].drop_duplicates().to_numpy()
        quantiles = predicted[columns].to_numpy().reshape(len(ids), H, len(columns))
        # A ordem das colunas segue os níveis pedidos; reordena por valor
        # médio por garantia (o MQLoss não impede cruzamento de quantis).
        order = np.argsort(quantiles.mean(axis=(0, 1)))
        quantiles = quantiles[:, :, order]

        for h in HORIZONS:
            ds = origin + pd.DateOffset(months=h)
            if ds > TEST_TARGETS[1]:
                continue
            target = targets.reindex(pd.MultiIndex.from_arrays([ids, np.repeat(ds, len(ids))]))
            valid = (target["outbreak"] >= 0).to_numpy()
            cut = np.maximum(np.floor(target["threshold"].to_numpy()) + 1, MIN_CASES[level]) - 0.5
            frames.append(
                pd.DataFrame(
                    {
                        "level": level, "series_id": ids[valid], "disease": target["disease"].to_numpy()[valid],
                        "state": target["state"].to_numpy()[valid], "ds": ds, "horizon": h,
                        "probability": exceed_probability(quantiles[valid, h - 1, :], CHRONOS_LEVELS, cut[valid]),
                    }
                )
            )
    print(f"{name} {level}: total {time.time() - start:.0f}s", flush=True)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", choices=["patchtst", "tft"])
    parser.add_argument("--steps", type=int, default=STEPS)
    parser.add_argument("--levels", nargs="+", default=["uf", "municipio"])
    args = parser.parse_args()
    for level in args.levels:
        save_alert(run_level(args.name, level, args.steps), f"{args.name}_{level}")


if __name__ == "__main__":
    main()
