"""
Parte B, modelos de fundação (zero-shot) no alerta. A cada origem
mensal t (dez/2022 a nov/2025) cada modelo prevê os quantis de t+1 a
t+3; a probabilidade de surto é P(casos >= menor contagem que é surto),
lida da distribuição montada com os quantis.

Uso: python alert_foundation.py <modelo> [uf] [municipio]
(modelos em MODELS; um por processo: as bibliotecas conflitam entre si).

chronos2_clima usa o clima passado como covariável (na origem o clima
dos meses previstos ainda não é conhecido). chronos2_completo soma as
covariáveis de ambiente (anuais) como conhecidas no futuro, com o
último valor da série. chronos2_cross_prev_* simulam uma previsão do
tempo para os meses-alvo (ver climate_forecast). TimesFM e Moirai: só
casos.
"""

import sys
import time

import numpy as np
import pandas as pd

from alert_features import load_labels
from common import (
    CALIBRATION_TARGETS,
    CLIMATE,
    COVARIATES,
    HORIZONS,
    MIN_CASES,
    TEST_TARGETS,
    TRAIN_TARGETS,
    exceed_probability,
    save_alert,
)

H = max(HORIZONS)
ORIGINS = pd.date_range(CALIBRATION_TARGETS[0] - pd.DateOffset(months=1), TEST_TARGETS[1] - pd.DateOffset(months=1), freq="MS")
CHRONOS_LEVELS = np.array([0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99])
DECILES = np.linspace(0.1, 0.9, 9)


def fill_by_series(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Buracos: último valor da série, depois a mediana da série, depois a geral."""

    df[columns] = df.groupby("item_id")[columns].ffill()
    df[columns] = df[columns].fillna(df.groupby("item_id")[columns].transform("median")).fillna(df[columns].median())
    return df


FORECAST_SKILL = {"perfeita": 1.0, "parcial": 0.5, "climatologia": 0.0}


def climate_forecast(labels: pd.DataFrame, ids: np.ndarray, steps: pd.DatetimeIndex, mode: str) -> pd.DataFrame:
    """
    Clima "previsto" para os meses-alvo, simulando uma previsão do tempo:
    normal do mês (média da série até o fim do treino) + skill × anomalia
    observada. perfeita = o clima que ocorreu (limite superior);
    parcial = metade da anomalia; climatologia = só a normal (controle,
    nenhuma informação nova). Mês sem observação (após dez/2025): normal.
    """

    skill = FORECAST_SKILL[mode]
    train = labels[labels["ds"] <= TRAIN_TARGETS[1]]
    normal_by_month = train.groupby(["series_id", train["ds"].dt.month])[CLIMATE].mean()
    item, timestamp = np.repeat(ids, len(steps)), np.tile(steps, len(ids))
    month = pd.DatetimeIndex(timestamp).month
    normal = normal_by_month.reindex(pd.MultiIndex.from_arrays([item, month])).to_numpy(dtype=float, na_value=np.nan)
    observed = labels.set_index(["series_id", "ds"])[CLIMATE].reindex(pd.MultiIndex.from_arrays([item, timestamp]))
    observed = observed.to_numpy(dtype=float, na_value=np.nan)
    observed = np.where(np.isnan(observed), normal, observed)
    future = pd.DataFrame(normal + skill * (observed - normal), columns=CLIMATE)
    return future.assign(item_id=item, timestamp=timestamp)


def chronos(with_climate: bool, with_environment: bool = False, cross_learning: bool = False,
            forecast: str | None = None):
    import torch
    from chronos import BaseChronosPipeline

    pipeline = BaseChronosPipeline.from_pretrained("amazon/chronos-2", device_map="cuda", torch_dtype=torch.bfloat16)
    past = CLIMATE if with_climate or forecast else []
    known = COVARIATES if with_environment else []  # anuais: o valor do mês-alvo já é conhecido na origem

    def predict(history: pd.DataFrame, labels: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        df = history[["series_id", "ds", "y", *past, *known]].rename(
            columns={"series_id": "item_id", "ds": "timestamp", "y": "target"}
        )
        future = None
        if forecast:  # clima dos meses-alvo vira covariável conhecida no futuro
            steps = pd.date_range(df["timestamp"].max(), periods=H + 1, freq="MS")[1:]
            future = climate_forecast(labels, np.sort(df["item_id"].unique()), steps, forecast)
        if known:
            df = fill_by_series(df, known)
            last = df.groupby("item_id", sort=True)[known].last()
            steps = pd.date_range(df["timestamp"].max(), periods=H + 1, freq="MS")[1:]
            future = last.loc[last.index.repeat(H)].reset_index().assign(timestamp=np.tile(steps, len(last)))
        # cross_learning: o modelo lê o lote junto. Com os ids em ordem
        # ("DOENÇA|UF" ou "DOENÇA|município"), um lote de ~100 séries reúne a
        # mesma doença em UFs/municípios vizinhos (tamanho do relatório técnico).
        out = pipeline.predict_df(
            df, future_df=future, prediction_length=H, quantile_levels=list(CHRONOS_LEVELS),
            batch_size=100 if cross_learning else 512, cross_learning=cross_learning, freq="MS",
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

    def predict(history: pd.DataFrame, labels: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
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

    def predict(history: pd.DataFrame, labels: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        past = [g.to_numpy(dtype=np.float32)[-120:, None] for _, g in history.groupby("series_id", sort=True)["y"]]
        chunks = [np.asarray(model.predict(past[i:i + 512])) for i in range(0, len(past), 512)]
        q = np.concatenate(chunks)[:, :, :H]  # [série, quantil 0.1..0.9, tempo]
        return np.transpose(q, (0, 2, 1)), DECILES

    return predict


MODELS = {
    "chronos2": lambda: chronos(False),
    "chronos2_clima": lambda: chronos(True),
    "chronos2_completo": lambda: chronos(True, with_environment=True),
    "chronos2_clima_cross": lambda: chronos(True, cross_learning=True),
    "chronos2_cross_prev_perfeita": lambda: chronos(True, cross_learning=True, forecast="perfeita"),
    "chronos2_cross_prev_parcial": lambda: chronos(True, cross_learning=True, forecast="parcial"),
    "chronos2_cross_climatologia": lambda: chronos(True, cross_learning=True, forecast="climatologia"),
    "timesfm": timesfm_model,
    "moirai2": moirai_model,
}


def run_level(predict, level: str) -> pd.DataFrame:
    labels = load_labels(level)
    targets = labels.set_index(["series_id", "ds"])[["threshold", "outbreak", "disease", "state"]]
    frames = []
    for origin in ORIGINS:
        history = labels[labels["ds"] <= origin]
        quantiles, levels = predict(history, labels)
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


def main(name: str, levels: list[str]) -> None:
    predict = MODELS[name]()
    for level in levels:
        start = time.time()
        save_alert(run_level(predict, level), f"{name}_{level}")
        print(f"{name} {level}: {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["uf", "municipio"])
