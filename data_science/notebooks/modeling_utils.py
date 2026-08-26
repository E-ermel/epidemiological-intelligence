"""Funções auxiliares para a modelagem estatística por doença.

Reproduz a metodologia definida em `data_science/notebooks/02_modeling.ipynb`
(modelo Binomial Negativo com efeitos de município e mês, testes climáticos
individuais, testes de lag, seleção de features e backtest temporal),
evitando duplicação de código entre os notebooks de cada doença.

Convenções fixas do projeto (não alterar sem revisar todos os notebooks):
- corte temporal treino/teste: 2024-01-01 (treino < corte, teste >= corte);
- nunca usar split aleatório;
- comparações de modelo sempre feitas sobre as mesmas linhas válidas;
- NaN climático nunca é preenchido com zero — é removido via dropna.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import patsy
import statsmodels.formula.api as smf
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.discrete.count_model import ZeroInflatedNegativeBinomialP
from statsmodels.genmod.bayes_mixed_glm import PoissonBayesMixedGLM

PROJECT_ID = "affable-alpha-506516-r7"
TABLE = "affable-alpha-506516-r7.epidemiological_intelligence.epidemiology_climate_monthly"

TRAIN_CUTOFF = pd.Timestamp("2024-01-01")
TRAIN_START = pd.Timestamp("2015-01-01")
TEST_END = pd.Timestamp("2025-12-31")

# Usado SOMENTE para seleção de variáveis/lags (nunca para o modelo final).
# 2023 fica reservado como validação, para que 2024-2025 nunca seja usado
# tanto para escolher features quanto para reportar a performance final —
# evita o viés otimista de "espiar" repetidamente o conjunto de teste ao
# testar ~10-25 variáveis/lags candidatas por doença.
VALIDATION_CUTOFF = pd.Timestamp("2023-01-01")

BASE_FORMULA = "cases ~ C(municipality) + C(month)"

CLIMATE_VARS = [
    "temperature_avg_c",
    "dew_point_avg_c",
    "relative_humidity_avg_pct",
    "atmospheric_pressure_avg_mb",
    "wind_speed_avg_ms",
    "wind_gust_max_ms",
    "precipitation_sum_mm",
    "precipitation_avg_observation_mm",
    "precipitation_max_observation_mm",
]

LAGS = (1, 2, 3)

DISEASES = {
    "asma": "ASMA",
    "bronquite_aguda": "BRONQUITE AGUDA",
    "bronquite_cronica": "BRONQUITE CRÔNICA",
    "infarto": "INFARTO AGUDO DO MIOCÁRDIO",
    "insuficiencia_cardiaca": "INSUFICIÊNCIA CARDÍACA",
    "leptospirose": "LEPTOSPIROSE",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_CACHE_PATH = REPO_ROOT / "data_science" / "data" / "raw" / "epidemiology_climate_monthly.parquet"
CLIMATE_LAG_CACHE_PATH = REPO_ROOT / "data_science" / "data" / "processed" / "climate_monthly_lags.parquet"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "modeling"


# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------

def load_raw_data(use_cache: bool = True, force_refresh: bool = False) -> pd.DataFrame:
    """Carrega a tabela `epidemiology_climate_monthly` do BigQuery.

    Usa um cache local em parquet (somente leitura do BigQuery, nunca grava
    de volta) para evitar re-consultar a mesma tabela em cada notebook de
    doença. `force_refresh=True` ignora o cache e busca dados atualizados.
    """
    if use_cache and not force_refresh and RAW_CACHE_PATH.exists():
        df = pd.read_parquet(RAW_CACHE_PATH)
        df["reference_date"] = pd.to_datetime(df["reference_date"])
        return df

    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT *
        FROM `{TABLE}`
        ORDER BY reference_date, municipality, disease
    """
    df = client.query(query).to_dataframe()
    df["reference_date"] = pd.to_datetime(df["reference_date"])

    RAW_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RAW_CACHE_PATH, index=False)
    return df


def temporal_split(df: pd.DataFrame, cutoff: pd.Timestamp = TRAIN_CUTOFF) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide temporalmente (nunca aleatoriamente) em treino/teste."""
    train = df[df["reference_date"] < cutoff].copy()
    test = df[df["reference_date"] >= cutoff].copy()
    return train, test


def feature_selection_split(train_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide o período de treino (< 2024) em treino-para-seleção (< 2023) e
    validação (2023), a serem usados EXCLUSIVAMENTE por
    `evaluate_candidate_features` (testes climáticos individuais e de lag).

    O modelo final continua sendo treinado em todo o período < 2024 e
    avaliado em 2024-2025 (via `temporal_split`/`fit_final_models`), sem
    nenhuma mudança nesse contrato. O que muda é que a BUSCA por quais
    variáveis/lags entram no modelo final passa a ser decidida olhando para
    2023 (validação), nunca para 2024-2025 (teste), eliminando o viés de
    "escolher a variável que parecia melhor no próprio conjunto de teste".
    """
    train_fs = train_df[train_df["reference_date"] < VALIDATION_CUTOFF].copy()
    validation_fs = train_df[train_df["reference_date"] >= VALIDATION_CUTOFF].copy()
    return train_fs, validation_fs


def prepare_disease_frame(df: pd.DataFrame, disease: str, feature_cols: Sequence[str] = ()) -> pd.DataFrame:
    """Filtra a doença e ajusta os tipos exigidos por patsy/statsmodels.

    Remove (não preenche) linhas com valores ausentes nas colunas exigidas.
    """
    required_cols = ["cases", "municipality", "month"] + list(feature_cols)
    out = df[df["disease"] == disease].dropna(subset=required_cols).copy()
    out["cases"] = out["cases"].astype("float64")
    out["month"] = out["month"].astype("int64")
    out["municipality"] = out["municipality"].astype(str)
    for col in feature_cols:
        out[col] = out[col].astype("float64")
    return out


def unseen_municipalities(train_df: pd.DataFrame, test_df: pd.DataFrame) -> set:
    """Municípios presentes no teste mas ausentes no treino válido do modelo."""
    return set(test_df["municipality"].unique()) - set(train_df["municipality"].unique())


def drop_unseen_municipalities(train_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, set]:
    """Remove do teste municípios não observados no treino (não inventa categoria)."""
    unseen = unseen_municipalities(train_df, test_df)
    filtered = test_df[~test_df["municipality"].isin(unseen)].copy()
    return filtered, unseen


# ---------------------------------------------------------------------------
# Lags climáticos (construídos em tabela própria, uma linha por município/mês)
# ---------------------------------------------------------------------------

def build_climate_monthly_lags(
    df: pd.DataFrame,
    lag_variables: Sequence[str] = tuple(CLIMATE_VARS),
    lags: Sequence[int] = LAGS,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Cria a tabela climática única por município/mês e os lags de 1..N meses.

    Os lags NÃO são feitos sobre o dataframe epidemiológico (que tem várias
    doenças por município/mês); são calculados aqui e depois mesclados de
    volta via `merge_climate_lags`. Valida ausência de duplicatas e de
    quebras na sequência mensal antes de gerar os lags.
    """
    if use_cache and CLIMATE_LAG_CACHE_PATH.exists():
        return pd.read_parquet(CLIMATE_LAG_CACHE_PATH)

    lag_variables = list(dict.fromkeys(lag_variables))
    climate_cols = ["municipality", "reference_date"] + lag_variables

    conflicts = (
        df[climate_cols]
        .groupby(["municipality", "reference_date"])
        .nunique(dropna=False)
    )
    conflict_count = int((conflicts > 1).any(axis=1).sum())
    if conflict_count != 0:
        raise ValueError(
            f"Existem {conflict_count} combinações município/mês com valores "
            "climáticos conflitantes."
        )

    climate_monthly = (
        df[climate_cols]
        .drop_duplicates(subset=["municipality", "reference_date"])
        .sort_values(["municipality", "reference_date"])
        .reset_index(drop=True)
    )

    duplicates = int(climate_monthly.duplicated(subset=["municipality", "reference_date"]).sum())
    if duplicates != 0:
        raise ValueError("A tabela climática ainda possui duplicatas município/mês.")

    check_dates = climate_monthly[["municipality", "reference_date"]].copy()
    check_dates["previous_date"] = check_dates.groupby("municipality")["reference_date"].shift(1)
    check_dates["month_difference"] = (
        (check_dates["reference_date"].dt.year * 12 + check_dates["reference_date"].dt.month)
        - (check_dates["previous_date"].dt.year * 12 + check_dates["previous_date"].dt.month)
    )
    gaps = check_dates[check_dates["previous_date"].notna() & (check_dates["month_difference"] != 1)]
    if len(gaps) != 0:
        raise ValueError(
            f"Existem {len(gaps)} quebras na sequência mensal por município; "
            "os lags precisam ser construídos por chave temporal contínua."
        )

    for variable in lag_variables:
        for lag in lags:
            climate_monthly[f"{variable}_lag{lag}"] = (
                climate_monthly.groupby("municipality")[variable].shift(lag)
            )

    CLIMATE_LAG_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    climate_monthly.to_parquet(CLIMATE_LAG_CACHE_PATH, index=False)
    return climate_monthly


def merge_climate_lags(df: pd.DataFrame, climate_monthly: pd.DataFrame) -> pd.DataFrame:
    """Mescla os lags de volta ao dataframe epidemiológico (many_to_one)."""
    lag_cols = [c for c in climate_monthly.columns if "_lag" in c]
    merged = df.merge(
        climate_monthly[["municipality", "reference_date"] + lag_cols],
        on=["municipality", "reference_date"],
        how="left",
        validate="many_to_one",
    )
    dup = int(merged.groupby(["disease", "municipality", "reference_date"]).size().gt(1).sum())
    if dup != 0:
        raise ValueError("O merge dos lags criou duplicatas disease/municipality/reference_date.")
    return merged


def lag_candidates(variables: Sequence[str], lags: Sequence[int] = LAGS) -> list[str]:
    """Lista 'atual + lag1 + lag2 + lag3' para cada variável, na ordem da metodologia."""
    candidates = []
    for variable in variables:
        candidates.append(variable)
        for lag in lags:
            candidates.append(f"{variable}_lag{lag}")
    return candidates


# ---------------------------------------------------------------------------
# Ajuste de modelos e métricas
# ---------------------------------------------------------------------------

def fit_negbin(formula: str, data: pd.DataFrame, method: str = "bfgs", maxiter: int = 500):
    """Ajusta Binomial Negativa com alpha estimado (nunca alpha=1 default)."""
    return smf.negativebinomial(formula=formula, data=data).fit(
        method=method, maxiter=maxiter, disp=False
    )


def regression_metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

    denom = np.abs(y_true).sum()
    wape = float(np.abs(y_true - y_pred).sum() / denom * 100) if denom != 0 else np.nan

    if len(np.unique(y_true)) > 1:
        r2 = float(r2_score(y_true, y_pred))
    else:
        r2 = np.nan

    return {"mae": mae, "rmse": rmse, "r2": r2, "wape_pct": wape}


def improvement_pct(base_value: float, value: float) -> float:
    if base_value is None or pd.isna(base_value) or base_value == 0:
        return np.nan
    return (base_value - value) / base_value * 100


def evaluate_candidate_features(
    train_disease: pd.DataFrame,
    test_disease: pd.DataFrame,
    candidates: Iterable[str],
    base_formula: str = BASE_FORMULA,
    method: str = "bfgs",
    maxiter: int = 500,
) -> pd.DataFrame:
    """Testa cada variável candidata individualmente contra o modelo-base.

    Usado tanto para os testes climáticos individuais (3.3) quanto para os
    testes de lag (3.4) — a única diferença é a lista de candidatos. A
    comparação é sempre feita sobre exatamente as mesmas linhas válidas da
    variável testada (dropna aplicado por variável, base e clima ajustados
    nas mesmas linhas de treino/teste).
    """
    required_base = ["cases", "municipality", "month"]
    results = []

    for variable in candidates:
        required_cols = required_base + [variable]
        train_var = train_disease.dropna(subset=required_cols).copy()
        test_var = test_disease.dropna(subset=required_cols).copy()

        # Não inventar categoria: um município que só aparece no teste (não
        # visto no treino válido desta variável) não pode ser escorado por um
        # modelo formula-api com C(municipality) — patsy rejeita o nível
        # desconhecido. Ele é excluído desta comparação (mesmo tratamento
        # aplicado no modelo final via `unseen_municipalities`).
        train_municipalities = set(train_var["municipality"].unique())
        test_var = test_var[test_var["municipality"].isin(train_municipalities)].copy()

        if len(train_var) == 0 or len(test_var) == 0:
            continue

        for dataset in (train_var, test_var):
            dataset["cases"] = dataset["cases"].astype("float64")
            dataset["month"] = dataset["month"].astype("int64")
            dataset["municipality"] = dataset["municipality"].astype(str)
            dataset[variable] = dataset[variable].astype("float64")

        try:
            base_model = fit_negbin(base_formula, train_var, method=method, maxiter=maxiter)
            climate_formula = f"{base_formula} + {variable}"
            climate_model = fit_negbin(climate_formula, train_var, method=method, maxiter=maxiter)

            base_pred = base_model.predict(test_var)
            climate_pred = climate_model.predict(test_var)

            base_mae = mean_absolute_error(test_var["cases"], base_pred)
            mae = mean_absolute_error(test_var["cases"], climate_pred)
            base_rmse = np.sqrt(mean_squared_error(test_var["cases"], base_pred))
            rmse = np.sqrt(mean_squared_error(test_var["cases"], climate_pred))

            results.append({
                "variable": variable,
                "train_n": len(train_var),
                "test_n": len(test_var),
                "coef": climate_model.params.get(variable, np.nan),
                "pvalue": climate_model.pvalues.get(variable, np.nan),
                "alpha": climate_model.params.get("alpha", np.nan),
                "base_mae": base_mae,
                "mae": mae,
                "mae_improvement_pct": improvement_pct(base_mae, mae),
                "base_rmse": base_rmse,
                "rmse": rmse,
                "rmse_improvement_pct": improvement_pct(base_rmse, rmse),
                "base_converged": bool(base_model.mle_retvals.get("converged", False)),
                "converged": bool(climate_model.mle_retvals.get("converged", False)),
            })
        except Exception as exc:  # noqa: BLE001 - segue para a próxima variável
            print(f"Erro em {variable}: {exc}")

    return (
        pd.DataFrame(results)
        .sort_values("mae_improvement_pct", ascending=False)
        .reset_index(drop=True)
    )


def build_formula(features: Sequence[str], base_formula: str = BASE_FORMULA) -> str:
    if not features:
        return base_formula
    return base_formula + " + " + " + ".join(features)


def fit_final_models(
    train_disease: pd.DataFrame,
    test_disease: pd.DataFrame,
    features: Sequence[str],
    base_formula: str = BASE_FORMULA,
    method: str = "bfgs",
    maxiter: int = 500,
) -> dict:
    """Ajusta o modelo-base (município+mês) e o modelo multivariado final.

    Ambos são ajustados e avaliados exatamente sobre as mesmas linhas
    (dropna aplicado uma única vez, considerando todas as features finais).
    """
    required_cols = ["cases", "municipality", "month"] + list(features)
    train_final = train_disease.dropna(subset=required_cols).copy()
    test_final = test_disease.dropna(subset=required_cols).copy()

    # Não inventar categoria: municípios presentes no teste mas ausentes do
    # treino válido (por causa do dropna acima) são excluídos daqui — o
    # notebook lista essa exclusão explicitamente via `unseen_municipalities`
    # aplicado às mesmas linhas de entrada usadas nesta função.
    train_municipalities = set(train_final["municipality"].unique())
    test_final = test_final[test_final["municipality"].isin(train_municipalities)].copy()

    for dataset in (train_final, test_final):
        dataset["cases"] = dataset["cases"].astype("float64")
        dataset["month"] = dataset["month"].astype("int64")
        dataset["municipality"] = dataset["municipality"].astype(str)
        for col in features:
            dataset[col] = dataset[col].astype("float64")

    base_model = fit_negbin(base_formula, train_final, method=method, maxiter=maxiter)
    final_formula = build_formula(features, base_formula)
    final_model = fit_negbin(final_formula, train_final, method=method, maxiter=maxiter)

    base_pred = base_model.predict(test_final)
    final_pred = final_model.predict(test_final)

    base_metrics = regression_metrics(test_final["cases"], base_pred)
    final_metrics = regression_metrics(test_final["cases"], final_pred)

    return {
        "train_final": train_final,
        "test_final": test_final,
        "base_model": base_model,
        "final_model": final_model,
        "base_pred": base_pred,
        "final_pred": final_pred,
        "base_metrics": base_metrics,
        "final_metrics": final_metrics,
        "mae_improvement_pct": improvement_pct(base_metrics["mae"], final_metrics["mae"]),
        "rmse_improvement_pct": improvement_pct(base_metrics["rmse"], final_metrics["rmse"]),
        "base_converged": bool(base_model.mle_retvals.get("converged", False)),
        "final_converged": bool(final_model.mle_retvals.get("converged", False)),
        "alpha": float(final_model.params.get("alpha", np.nan)),
        "formula": final_formula,
    }


def municipality_metrics_table(eval_df: pd.DataFrame, cases_col: str = "cases", pred_col: str = "prediction") -> pd.DataFrame:
    """Tabela de MAE/RMSE/WAPE/R² por município.

    IMPORTANTE: não interpretar WAPE como "acurácia", especialmente para
    municípios com poucos casos ou zero casos.
    """
    rows = []
    for municipality, group in eval_df.groupby("municipality"):
        metrics = regression_metrics(group[cases_col], group[pred_col])
        rows.append({
            "municipality": municipality,
            "n": len(group),
            "mean_cases": group[cases_col].mean(),
            "mae": metrics["mae"],
            "rmse": metrics["rmse"],
            "wape_pct": metrics["wape_pct"],
            "r2": metrics["r2"],
        })
    return pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def plot_real_vs_predicted(y_true, y_pred, disease: str):
    plt.figure(figsize=(8, 8))
    plt.scatter(y_true, y_pred, alpha=0.5)

    max_value = max(np.max(y_true), np.max(y_pred))
    plt.plot([0, max_value], [0, max_value], linestyle="--", color="gray")

    plt.xlabel("Casos reais")
    plt.ylabel("Casos previstos")
    plt.title(f"{disease} — Real vs Previsto (2024–2025)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


def make_backtest_plotter(disease: str, historical_df: pd.DataFrame, forecast_df: pd.DataFrame):
    """Retorna uma função `plot_backtest(municipality)` fechada sobre os dados da doença.

    `historical_df`: linhas de treino (2015-2023) com coluna `cases`.
    `forecast_df`: linhas de teste (2024-2025) com colunas `cases` e `prediction`.
    """

    def plot_backtest(municipality: str):
        hist = (
            historical_df[historical_df["municipality"] == municipality]
            .sort_values("reference_date")
        )
        fut = (
            forecast_df[forecast_df["municipality"] == municipality]
            .sort_values("reference_date")
        )

        if len(hist) == 0 and len(fut) == 0:
            print(f"Sem dados para {municipality}.")
            return

        plt.figure(figsize=(16, 6))

        plt.plot(hist["reference_date"], hist["cases"], linewidth=2, label="Real — treinamento")
        plt.plot(fut["reference_date"], fut["cases"], linewidth=2, marker="o", label="Real — teste")
        plt.plot(
            fut["reference_date"], fut["prediction"],
            linewidth=2, linestyle="--", marker="o", label="Previsto — teste"
        )

        plt.axvline(TRAIN_CUTOFF, linestyle="--", linewidth=2, color="black", label="Início da previsão")

        plt.title(f"{disease} — {municipality}\nTreinamento: 2015–2023 | Previsão: 2024–2025")
        plt.xlabel("Ano")
        plt.ylabel("Número de casos")
        plt.legend()
        plt.grid(alpha=0.3)
        plt.xlim(TRAIN_START, TEST_END)
        plt.tight_layout()
        plt.show()

    return plot_backtest


def plot_baseline_vs_climate(disease: str, municipality: str, plot_df: pd.DataFrame):
    """`plot_df` (2024-2025, um município) precisa ter as colunas cases, baseline_pred, climate_pred."""
    plot_df = plot_df.sort_values("reference_date")

    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["reference_date"], plot_df["cases"], marker="o", label="Real")
    plt.plot(plot_df["reference_date"], plot_df["baseline_pred"], linestyle="--", label="Baseline (município + mês)")
    plt.plot(plot_df["reference_date"], plot_df["climate_pred"], marker="o", label="Modelo climático")

    plt.title(f"{disease} — Baseline vs modelo climático\n{municipality} (2024–2025)")
    plt.xlabel("Data")
    plt.ylabel("Casos")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Persistência de artefatos
# ---------------------------------------------------------------------------

def _json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    raise TypeError(f"Objeto do tipo {type(obj)} não é serializável em JSON")


def save_disease_artifacts(disease_key: str, metrics: dict, predictions_df: pd.DataFrame | None = None) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    metrics_path = ARTIFACTS_DIR / f"{disease_key}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=_json_default)

    if predictions_df is not None:
        predictions_path = ARTIFACTS_DIR / f"{disease_key}_predictions.parquet"
        predictions_df.to_parquet(predictions_path, index=False)


def load_disease_artifacts(disease_key: str) -> tuple[dict, pd.DataFrame | None]:
    metrics_path = ARTIFACTS_DIR / f"{disease_key}_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    predictions_path = ARTIFACTS_DIR / f"{disease_key}_predictions.parquet"
    predictions = pd.read_parquet(predictions_path) if predictions_path.exists() else None

    return metrics, predictions


# ---------------------------------------------------------------------------
# Pooling do efeito climático: pooled (oficial) vs não-pooled vs parcialmente
# pooled, e Zero-Inflated NB — experimentos exploratórios, não substituem o
# modelo oficial de cada doença a menos que superem-no de forma clara e
# consistente. Ver notebooks de doença, seção "Pooling do efeito climático".
# ---------------------------------------------------------------------------

def _dropna_for_features(df: pd.DataFrame, features: Sequence[str]) -> pd.DataFrame:
    """Garante linhas completas para município/mês/features, independente do
    dataframe recebido já estar limpo ou não. As três funções de pooling
    abaixo chamam isso internamente (não dependem do chamador ter feito o
    dropna correto primeiro) — evita o mesmo desalinhamento de linhas entre
    o design fixo e o design aleatório que já apareceu quando o dataframe
    de entrada ainda tinha NaN nas features.
    """
    required_cols = ["cases", "municipality", "month"] + list(features)
    out = df.dropna(subset=required_cols).copy()
    out["cases"] = out["cases"].astype("float64")
    out["month"] = out["month"].astype("int64")
    out["municipality"] = out["municipality"].astype(str)
    for col in features:
        out[col] = out[col].astype("float64")
    return out


def fit_interaction_model(
    train_disease: pd.DataFrame,
    test_disease: pd.DataFrame,
    features: Sequence[str],
    base_formula: str = BASE_FORMULA,
    method: str = "bfgs",
    maxiter: int = 2000,
) -> dict:
    """Modelo NÃO-POOLED para o efeito climático: cada município recebe seu
    próprio coeficiente para cada feature (`C(municipality):feature`), em vez
    do único coeficiente compartilhado do modelo oficial (pooled). Município
    e mês continuam como efeitos fixos normais. Usa as mesmas linhas de
    `train_disease`/`test_disease` já preparadas por `fit_final_models`
    (dropna/tipos/filtro de município não visto já aplicados).

    Espera-se mais ruído por município (menos dados por combinação
    município×feature) — é um experimento para checar se o efeito do clima
    parece variar entre municípios, não uma melhoria garantida.
    """
    train_disease = _dropna_for_features(train_disease, features)
    test_disease = _dropna_for_features(test_disease, features)
    train_municipalities = set(train_disease["municipality"].unique())
    test_disease = test_disease[test_disease["municipality"].isin(train_municipalities)]

    interaction_terms = " + ".join(f"C(municipality):{f}" for f in features)
    formula = f"{base_formula} + {interaction_terms}"

    model = fit_negbin(formula, train_disease, method=method, maxiter=maxiter)
    pred = np.asarray(model.predict(test_disease), dtype=float)
    stable = bool(np.all(np.isfinite(pred)) and pred.max() < 1e6)
    metrics = regression_metrics(test_disease["cases"], pred) if stable else None

    return {
        "model": model,
        "pred": pred,
        "metrics": metrics,
        "stable": stable,
        "converged": bool(model.mle_retvals.get("converged", False)),
        "formula": formula,
        "n_params": len(model.params),
    }


def fit_hierarchical_random_slope(
    train_disease: pd.DataFrame,
    test_disease: pd.DataFrame,
    features: Sequence[str],
) -> dict:
    """Modelo PARCIALMENTE POOLED (Poisson hierárquico, via Bayes
    variacional): intercepto aleatório por município + uma inclinação
    aleatória por município para cada feature climática. Diferente do modelo
    de interação (não-pooled), aqui os coeficientes por município são
    "encolhidos" em direção à média geral — municípios com poucos dados
    tomam emprestada força estatística dos demais.

    Limitação conhecida: é um Poisson (sem o parâmetro de dispersão extra
    `alpha` da Binomial Negativa), então overdispersion residual não
    capturada pelos efeitos aleatórios pode prejudicar o ajuste. As
    variáveis climáticas são padronizadas (z-score) apenas para estabilizar
    a otimização variacional — as previsões finais já voltam à escala
    original de `cases`.
    """
    train_disease = _dropna_for_features(train_disease, features)
    test_disease = _dropna_for_features(test_disease, features)
    train_municipalities = set(train_disease["municipality"].unique())
    test_disease = test_disease[test_disease["municipality"].isin(train_municipalities)]

    train_z = train_disease.copy()
    test_z = test_disease.copy()

    z_features = []
    for feature in features:
        mean_, std_ = train_z[feature].mean(), train_z[feature].std()
        z_col = f"_z_{feature}"
        train_z[z_col] = (train_z[feature] - mean_) / std_
        test_z[z_col] = (test_z[feature] - mean_) / std_
        z_features.append(z_col)

    fe_formula = "cases ~ C(month)" + ("".join(f" + {zf}" for zf in z_features))
    y, X = patsy.dmatrices(fe_formula, train_z, return_type="dataframe")

    z_intercept = patsy.dmatrix("0 + C(municipality)", train_z, return_type="dataframe")
    z_blocks = [z_intercept.values]
    ident_blocks = [np.zeros(z_intercept.shape[1], dtype=int)]
    for i, zf in enumerate(z_features, start=1):
        z_blocks.append(z_intercept.values * train_z[zf].values[:, None])
        ident_blocks.append(np.full(z_intercept.shape[1], i, dtype=int))

    z_design = np.concatenate(z_blocks, axis=1)
    ident = np.concatenate(ident_blocks)

    model = PoissonBayesMixedGLM(y.values.ravel(), X.values, z_design, ident)
    result = model.fit_vb()

    y_test, x_test = patsy.build_design_matrices(
        [y.design_info, X.design_info], test_z, return_type="dataframe"
    )
    z_intercept_test = patsy.build_design_matrices(
        [z_intercept.design_info], test_z, return_type="dataframe"
    )[0]
    z_test_blocks = [z_intercept_test.values]
    for zf in z_features:
        z_test_blocks.append(z_intercept_test.values * test_z[zf].values[:, None])
    z_design_test = np.concatenate(z_test_blocks, axis=1)

    lin_pred = x_test.values @ result.fe_mean + z_design_test @ result.vc_mean
    pred = np.exp(np.clip(lin_pred, -30, 30))
    stable = bool(np.all(np.isfinite(pred)) and pred.max() < 1e6)
    metrics = regression_metrics(test_z["cases"], pred) if stable else None

    return {
        "result": result,
        "pred": pred,
        "metrics": metrics,
        "stable": stable,
        "fe_formula": fe_formula,
    }


def fit_zinb(
    train_disease: pd.DataFrame,
    test_disease: pd.DataFrame,
    features: Sequence[str],
    base_formula: str = BASE_FORMULA,
    maxiter: int = 2000,
) -> dict:
    """Zero-Inflated Negative Binomial com inflação constante (intercepto
    apenas). Usado como experimento exploratório para doenças com alta
    proporção de zeros — verifica se um mecanismo explícito de "zero
    estrutural" agrega algo além do que os efeitos fixos de município já
    absorvem no modelo NB oficial.

    Tenta primeiro na escala original das variáveis; se a otimização não
    convergir ou produzir previsões instáveis, tenta novamente com as
    variáveis climáticas padronizadas (z-score) — algumas doenças convergem
    melhor numa escala, outras na outra, então as duas tentativas são
    genuínas, não uma "escolhida a dedo" para parecer melhor.
    """
    train_disease = _dropna_for_features(train_disease, features)
    test_disease = _dropna_for_features(test_disease, features)
    train_municipalities = set(train_disease["municipality"].unique())
    test_disease = test_disease[test_disease["municipality"].isin(train_municipalities)]

    def _try_fit(train_df: pd.DataFrame, test_df: pd.DataFrame, feats: Sequence[str]):
        formula = build_formula(feats, base_formula)
        y, X = patsy.dmatrices(formula, train_df, return_type="dataframe")
        y_test, x_test = patsy.build_design_matrices(
            [y.design_info, X.design_info], test_df, return_type="dataframe"
        )
        model = ZeroInflatedNegativeBinomialP(
            y, X, exog_infl=np.ones((len(y), 1)), inflation="logit"
        ).fit(method="bfgs", maxiter=maxiter, disp=False)
        pred = np.asarray(
            model.predict(x_test, exog_infl=np.ones((len(x_test), 1))), dtype=float
        )
        stable = bool(np.all(np.isfinite(pred)) and pred.max() < 1e6)
        converged = bool(model.mle_retvals.get("converged", False))
        metrics = regression_metrics(test_df["cases"], pred) if stable else None
        return {
            "model": model,
            "pred": pred,
            "metrics": metrics,
            "stable": stable,
            "converged": converged,
        }

    _failed_result = {"model": None, "pred": None, "metrics": None, "stable": False, "converged": False}

    try:
        raw_result = _try_fit(train_disease, test_disease, features)
    except Exception:
        raw_result = dict(_failed_result)

    if raw_result.get("stable") and raw_result.get("converged"):
        raw_result["scaling"] = "original"
        return raw_result

    train_z = train_disease.copy()
    test_z = test_disease.copy()
    z_features = []
    for feature in features:
        mean_, std_ = train_z[feature].mean(), train_z[feature].std()
        z_col = f"_z_{feature}"
        train_z[z_col] = (train_z[feature] - mean_) / std_
        test_z[z_col] = (test_z[feature] - mean_) / std_
        z_features.append(z_col)

    try:
        z_result = _try_fit(train_z, test_z, z_features)
        z_result["scaling"] = "standardized"
    except Exception:
        z_result = {"stable": False, "converged": False, "scaling": "standardized",
                     "model": None, "pred": None, "metrics": None}

    # Devolve o melhor dos dois resultados tentados (prioriza convergência+estabilidade).
    if z_result.get("stable") and z_result.get("converged"):
        return z_result
    return z_result if z_result.get("stable") else raw_result | {"scaling": "original"}
