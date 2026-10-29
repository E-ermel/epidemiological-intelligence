"""
Parte B, modelos de fundação (zero-shot) no alerta. A cada origem
mensal t (dez/2022 a nov/2025) cada modelo prevê os quantis de t+1 a
t+3; a probabilidade de surto é P(casos >= menor contagem que é surto),
lida da distribuição montada com os quantis.

Uso: python alert_foundation.py <chronos2|chronos2_clima|timesfm|moirai2>
(um modelo por processo: as bibliotecas conflitam entre si).

chronos2_clima usa o clima passado como covariável (na origem o clima
dos meses previstos ainda não é conhecido). TimesFM e Moirai: só casos.
"""

import sys
import time

import numpy as np
import pandas as pd

from alert_features import load_labels
from common import CALIBRATION_TARGETS, CLIMATE, HORIZONS, MIN_CASES, TEST_TARGETS, exceed_probability, save_alert

H = max(HORIZONS)
ORIGINS = pd.date_range(CALIBRATION_TARGETS[0] - pd.DateOffset(months=1), TEST_TARGETS[1] - pd.DateOffset(months=1), freq="MS")
CHRONOS_LEVELS = np.array([0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99])
DECILES = np.linspace(0.1, 0.9, 9)


def chronos(with_climate: bool):
    import torch
    from chronos import BaseChronosPipeline

    pipeline = BaseChronosPipeline.from_pretrained("amazon/chronos-2", device_map="cuda", torch_dtype=torch.bfloat16)
    covariates = CLIMATE if with_climate else []

    def predict(history: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        df = history[["series_id", "ds", "y", *covariates]].rename(
            columns={"series_id": "item_id", "ds": "timestamp", "y": "target"}
        )
        out = pipeline.predict_df(
            df, prediction_length=H, quantile_levels=list(CHRONOS_LEVELS), batch_size=512, freq="MS"
        ).sort_values(["item_id", "timestamp"])
        q = out[[str(level) for level in CHRONOS_LEVELS]].to_numpy().reshape(-1, H, len(CHRONOS_LEVELS))
        return q, CHRONOS_LEVELS

    return predict


def timesfm_model():
    import timesfm

    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
    model.compile(
        timesfm.ForecastConfig(
            max_context=128, max_horizon=16, normalize_inputs=True, use_continuous_quantile_head=True,
            infer_is_positive=True, fix_quantile_crossing=True, per_core_batch_size=1024,
        )
    )

    def predict(history: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        series = history.groupby("series_id", sort=True)["y"].apply(lambda s: s.to_numpy(dtype=np.float32)[-128:])
        _, quantiles = model.forecast(horizon=H, inputs=series.to_list())
        return np.asarray(quantiles)[:, :H, 1:10], DECILES  # índice 0 = média

    return predict


def moirai_model():
    from uni2ts.model.moirai2 import Moirai2Forecast, Moirai2Module

    model = Moirai2Forecast(
        module=Moirai2Module.from_pretrained("Salesforce/moirai-2.0-R-small"), prediction_length=H,
        context_length=120, target_dim=1, feat_dynamic_real_dim=0, past_feat_dynamic_real_dim=0,
    ).to("cuda")

    def predict(history: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        past = [g.to_numpy(dtype=np.float32)[-120:, None] for _, g in history.groupby("series_id", sort=True)["y"]]
        chunks = [np.asarray(model.predict(past[i:i + 512])) for i in range(0, len(past), 512)]
        q = np.concatenate(chunks)[:, :, :H]  # [série, quantil 0.1..0.9, tempo]
        return np.transpose(q, (0, 2, 1)), DECILES

    return predict


MODELS = {
    "chronos2": lambda: chronos(False),
    "chronos2_clima": lambda: chronos(True),
    "timesfm": timesfm_model,
    "moirai2": moirai_model,
}


def run_level(predict, level: str) -> pd.DataFrame:
    labels = load_labels(level)
    targets = labels.set_index(["series_id", "ds"])[["threshold", "outbreak", "disease", "state"]]
    frames = []
    for origin in ORIGINS:
        history = labels[labels["ds"] <= origin]
        quantiles, levels = predict(history)
        ids = np.sort(history["series_id"].unique())
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
                        "probability": exceed_probability(quantiles[valid, h - 1, :], levels, cut[valid]),
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def main(name: str) -> None:
    predict = MODELS[name]()
    for level in ("uf", "municipio"):
        start = time.time()
        save_alert(run_level(predict, level), f"{name}_{level}")
        print(f"{name} {level}: {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
