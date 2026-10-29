"""
Previsão do alerta: Chronos-2 (zero-shot) com o clima passado como
covariável e cross-learning, quantis de 1 a 3 meses à frente e a
probabilidade de passar do limite de surto.
"""

from typing import Protocol

import numpy as np
import pandas as pd

from epidemiological_intelligence.alert import config

H = max(config.HORIZONS)
LEVELS = np.array(config.QUANTILE_LEVELS)


class Forecaster(Protocol):
    def __call__(self, history: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """history (series_id, ds, y, clima) -> (ids ordenados, quantis [série, horizonte, nível])."""


def chronos_forecaster() -> Forecaster:
    import torch
    from chronos import BaseChronosPipeline

    pipeline = BaseChronosPipeline.from_pretrained(
        config.CHRONOS_MODEL, device_map=config.CHRONOS_DEVICE, torch_dtype=torch.float32
    )

    def predict(history: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        df = history[["series_id", "ds", "y", *config.CLIMATE]].rename(
            columns={"series_id": "item_id", "ds": "timestamp", "y": "target"}
        ).sort_values(["item_id", "timestamp"])
        out = pipeline.predict_df(
            df,
            prediction_length=H,
            quantile_levels=config.QUANTILE_LEVELS,
            batch_size=config.CROSS_LEARNING_BATCH,
            cross_learning=True,
            freq="MS",
        ).sort_values(["item_id", "timestamp"])
        ids = out["item_id"].drop_duplicates().to_numpy()
        quantiles = out[[str(level) for level in config.QUANTILE_LEVELS]].to_numpy()
        return ids, quantiles.reshape(len(ids), H, len(LEVELS))

    return predict


def exceed_probability(quantiles: np.ndarray, threshold: np.ndarray) -> np.ndarray:
    """
    P(Y > limite) a partir dos quantis previstos (linhas = previsões,
    colunas = níveis crescentes), interpolando a CDF entre os quantis.
    """

    quantiles = np.maximum.accumulate(quantiles, axis=1)
    cdf = np.array([np.interp(t, q, LEVELS, left=0.0, right=1.0) for q, t in zip(quantiles, threshold)])
    return 1 - cdf


def forecast_origin(
    panel: pd.DataFrame,
    level: str,
    diseases: list[str],
    origin: pd.Timestamp,
    origin_type: str,
    forecaster: Forecaster,
) -> pd.DataFrame:
    """Alertas de 1 a 3 meses para as doenças dadas, a partir de `origin`."""

    series = panel[panel["disease"].isin(diseases)]
    history = series[series["ds"] <= origin]
    ids, quantiles = forecaster(history)

    meta = series.drop_duplicates("series_id").set_index("series_id")
    by_month = series.set_index(["series_id", "ds"])
    frames = []
    for h in config.HORIZONS:
        target = origin + pd.DateOffset(months=h)
        rows = by_month.reindex(pd.MultiIndex.from_arrays([ids, np.repeat(target, len(ids))]))
        threshold = rows["threshold"].to_numpy(dtype=float)
        # Menor contagem que é surto: acima do limite e no mínimo
        # MIN_CASES; -0,5 põe o corte entre dois inteiros.
        cut = np.maximum(np.floor(threshold) + 1, config.MIN_CASES[level]) - 0.5
        q = quantiles[:, h - 1, :]
        valid = ~np.isnan(threshold)
        probability = np.full(len(ids), np.nan)
        probability[valid] = exceed_probability(q[valid], cut[valid])

        frames.append(
            pd.DataFrame(
                {
                    "origin_type": origin_type,
                    "origin_month": origin,
                    "level": level,
                    "disease": meta.loc[ids, "disease"].to_numpy(),
                    "source": meta.loc[ids, "source"].to_numpy(),
                    "state": meta.loc[ids, "state"].to_numpy(),
                    "municipality_code": (
                        meta.loc[ids, "municipality_code"].to_numpy() if level == "municipio" else None
                    ),
                    "target_month": target,
                    "horizon": h,
                    "threshold": threshold,
                    "cases_p10": q[:, list(LEVELS).index(0.1)],
                    "cases_p50": q[:, list(LEVELS).index(0.5)],
                    "cases_p90": q[:, list(LEVELS).index(0.9)],
                    "probability": probability,
                    "observed_cases": rows["y"].to_numpy(dtype=float),
                    "target_provisional": rows["is_provisional"].astype("boolean").to_numpy(),
                }
            )
        )
    out = pd.concat(frames, ignore_index=True)
    out = out[out["probability"].notna()]  # séries sem 5 anos de canal
    out["cutoff"] = config.CUTOFFS[level]
    out["alert"] = out["probability"] >= out["cutoff"]
    return out
