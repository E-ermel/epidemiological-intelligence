"""
Base comum do estudo (clima/ambiente x doença) e do teste de alerta de
surtos. Roda no venv de data_science/benchmarks (ver README).

- prepare.py: gold nacional -> painéis por município e por UF.
- study_dlnm.py / study_lgbm.py: parte A, relação entre fatores e casos.
- alert_*.py: parte B, alerta de surto; cada script grava as
  probabilidades de surto de um modelo em OUTPUT_DIR/alert/<modelo>.parquet
  e alert_evaluate.py calcula as métricas.
"""

import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path(os.getenv("STUDY_OUTPUT_DIR", Path(__file__).parent / "output"))
PANEL_PATHS = {"uf": OUTPUT_DIR / "panel_uf.parquet", "municipio": OUTPUT_DIR / "panel_municipio.parquet"}
ALERT_DIR = OUTPUT_DIR / os.getenv("STUDY_ALERT_DIR", "alert")

FIRST_MONTH = pd.Timestamp("2015-01-01")
LAST_MONTH = pd.Timestamp("2025-12-01")

# Clima do mês (o gold traz mais; estes cobrem chuva, chuva extrema,
# calor e umidade sem colunas quase iguais entre si).
CLIMATE = [
    "precipitation_sum_mm",
    "precipitation_max_observation_mm",
    "temperature_avg_c",
    "relative_humidity_avg_pct",
]
CLIMATE_LAGS = [0, 1, 2, 3]

# Ambiente e condições do município (anuais ou fixas).
COVARIATES = [
    "log_population_density",
    "land_forest_pct",
    "land_farming_pct",
    "land_urban_pct",
    "land_water_pct",
    "deforestation_pct",
    "snis_water_coverage_pct",
    "snis_sewage_coverage_pct",
    "snis_water_loss_distribution_pct",
    "atlas_idhm",
    "atlas_gini",
    "atlas_pct_inadequate_water_sewage",
    "atlas_pct_garbage_collection",
    "atlas_pct_urban",
]

LABELS = {
    "precipitation_sum_mm": "Chuva no mês",
    "precipitation_max_observation_mm": "Chuva extrema (máx. horária)",
    "temperature_avg_c": "Temperatura média",
    "relative_humidity_avg_pct": "Umidade relativa",
    "log_population_density": "Densidade populacional (log)",
    "land_forest_pct": "Floresta (% do território)",
    "land_farming_pct": "Agropecuária (%)",
    "land_urban_pct": "Área urbana (%)",
    "land_water_pct": "Água (%)",
    "deforestation_pct": "Desmatamento no ano (%)",
    "snis_water_coverage_pct": "Atendimento de água (%)",
    "snis_sewage_coverage_pct": "Atendimento de esgoto (%)",
    "snis_water_loss_distribution_pct": "Perdas de água (%)",
    "atlas_idhm": "IDHM",
    "atlas_gini": "Gini",
    "atlas_pct_inadequate_water_sewage": "Água/esgoto inadequados (%)",
    "atlas_pct_garbage_collection": "Coleta de lixo (%)",
    "atlas_pct_urban": "População urbana (%)",
    "month": "Mês do ano",
    "state": "UF",
    # Atributos do alerta (alert_features.py).
    "recent_cases": "Casos recentes (origem)",
    "same_month_past_years": "Mesmo mês, anos anteriores",
    "endemic_channel": "Canal endêmico do mês",
    "outbreak_origin": "Surto na origem",
    "log_population": "População (log)",
    "horizon": "Horizonte",
    "target_month": "Mês do ano",
    "disease": "Doença",
}

# --- Surto ---------------------------------------------------------
# Diagrama de controle: o mês está em surto quando os casos passam da
# média + 1,96 desvio-padrão do mesmo mês nos 5 anos anteriores e
# atingem um mínimo de casos (sem o mínimo, 1 caso numa série quase
# sempre zerada já seria "surto").
CHANNEL_YEARS = 5
CHANNEL_Z = 1.96
MIN_CASES = {"uf": 5, "municipio": 3}
# Anos que não entram no canal (ex.: "2020,2021", a queda de internações
# da pandemia baixa os limites e cria falsos surtos). O canal usa os 5
# anos anteriores mais recentes fora dessa lista.
CHANNEL_EXCLUDED_YEARS = [int(y) for y in os.getenv("STUDY_CHANNEL_EXCLUDE", "").split(",") if y]

# Série municipal entra no alerta com média >= 1 caso/mês até 2022;
# as demais ficam só no alerta da UF.
MIN_MEAN_CASES_MUNICIPIO = 1.0

HORIZONS = [1, 2, 3]
# Alvo (mês previsto) de cada fase do teste de alerta.
TRAIN_TARGETS = (pd.Timestamp("2020-01-01"), pd.Timestamp("2022-12-01"))
CALIBRATION_TARGETS = (pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-01"))
TEST_TARGETS = (pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-01"))

ALERT_COLUMNS = ["level", "series_id", "disease", "state", "ds", "horizon", "model", "probability"]


def series_keys(level: str) -> list[str]:
    return ["disease", "state"] if level == "uf" else ["disease", "municipality_code"]


def load_panel(level: str) -> pd.DataFrame:
    return pd.read_parquet(PANEL_PATHS[level])


def endemic_channel(panel: pd.DataFrame, level: str) -> pd.DataFrame:
    """Acrescenta threshold (limite do canal) e outbreak (0/1) por mês."""

    keys = series_keys(level)
    df = panel.sort_values([*keys, "ds"]).copy()
    df["calendar_month"] = df["ds"].dt.month

    # Agrupado por mês do calendário (grade mensal completa), shift(k) é
    # o mesmo mês k anos antes. Anos excluídos viram NaN e o canal pega
    # os CHANNEL_YEARS valores mais recentes que sobram.
    excluded = df["ds"].dt.year.isin(CHANNEL_EXCLUDED_YEARS)
    df["_y_channel"] = df["y"].where(~excluded)
    grouped = df.groupby([*keys, "calendar_month"])["_y_channel"]
    depth = CHANNEL_YEARS + len(CHANNEL_EXCLUDED_YEARS)
    past = np.column_stack([grouped.shift(k).to_numpy(dtype=float) for k in range(1, depth + 1)])
    valid = ~np.isnan(past)
    keep = valid & (np.cumsum(valid, axis=1) <= CHANNEL_YEARS)
    kept = np.where(keep, past, np.nan)
    enough = keep.sum(axis=1) == CHANNEL_YEARS
    with warnings.catch_warnings():  # linhas sem 5 anos: fatia vazia, viram NaN
        warnings.simplefilter("ignore", RuntimeWarning)
        df["channel_mean"] = np.where(enough, np.nanmean(kept, axis=1), np.nan)
        df["channel_sd"] = np.where(enough, np.nanstd(kept, axis=1, ddof=1), np.nan)
    df = df.drop(columns="_y_channel")
    df["threshold"] = df["channel_mean"] + CHANNEL_Z * df["channel_sd"]
    df["outbreak"] = ((df["y"] > df["threshold"]) & (df["y"] >= MIN_CASES[level])).astype("int8")
    df.loc[df["threshold"].isna(), "outbreak"] = -1  # sem 5 anos de histórico
    return df.drop(columns="calendar_month")


def save_alert(predictions: pd.DataFrame, model: str) -> Path:
    predictions = predictions.assign(model=model)
    missing = set(ALERT_COLUMNS) - set(predictions.columns)
    if missing:
        raise ValueError(f"Previsões sem as colunas {missing}")
    predictions["probability"] = predictions["probability"].clip(0, 1).astype("float64")

    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    path = ALERT_DIR / f"{model}.parquet"
    predictions[ALERT_COLUMNS].to_parquet(path, index=False)
    print(f"{model}: {len(predictions)} probabilidades em {path}")
    return path


def exceed_probability(quantiles: np.ndarray, levels: np.ndarray, threshold: np.ndarray) -> np.ndarray:
    """
    P(Y > limite) a partir de quantis previstos (linhas = previsões,
    colunas = níveis crescentes), interpolando a CDF entre os quantis.
    """

    quantiles = np.maximum.accumulate(quantiles, axis=1)
    cdf = np.empty(len(threshold))
    for i, (q, t) in enumerate(zip(quantiles, threshold)):
        cdf[i] = np.interp(t, q, levels, left=0.0, right=1.0)
    return 1 - cdf
