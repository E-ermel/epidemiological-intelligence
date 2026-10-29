"""
Parte A2: LightGBM (Poisson) por doença no painel município × mês, com
SHAP para medir quanto cada variável pesa na previsão.

Mesmas entradas do DLNM, sem casos passados (o estudo quer o efeito do
ambiente, não a inércia da série): clima com defasagem 0-3, mês do
ano, UF e covariáveis; log(população) entra como offset (init_score).
Treina em 2015-2023, testa em 2024-2025.

Saídas em OUTPUT_DIR/study/: lgbm_importance.csv (média do |SHAP| por
variável, defasagens somadas na variável de clima) e lgbm_metrics.csv.
"""

import time

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap

from common import CLIMATE, CLIMATE_LAGS, COVARIATES, LABELS, OUTPUT_DIR, load_panel

TRAIN_END = pd.Timestamp("2023-12-01")
MIN_TOTAL_CASES = 1000
SHAP_SAMPLE = 30_000
STUDY_DIR = OUTPUT_DIR / "study"

PARAMS = {
    "objective": "poisson",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_data_in_leaf": 200,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "verbose": -1,
}
ROUNDS = 600


def features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["municipality_code", "ds"])
    grouped = df.groupby("municipality_code")
    out = {f"{v}_l{lag}": grouped[v].shift(lag) for v in CLIMATE for lag in CLIMATE_LAGS}
    out["month"] = df["ds"].dt.month
    out["state"] = df["state"].astype("category")
    for column in COVARIATES:
        out[column] = df[column]
    return pd.DataFrame(out, index=df.index)


def base_variable(feature: str) -> str:
    for variable in CLIMATE:
        if feature.startswith(variable):
            return variable
    return feature


def fit_disease(disease: str, df: pd.DataFrame) -> tuple[list[dict], dict]:
    X = features(df)
    keep = X[[f"{v}_l{max(CLIMATE_LAGS)}" for v in CLIMATE]].notna().all(axis=1)
    X, df = X[keep], df.loc[X.index[keep]]
    offset = np.log(df["population"].to_numpy())
    train = (df["ds"] <= TRAIN_END).to_numpy()

    data = lgb.Dataset(X[train], df["y"][train], init_score=offset[train], categorical_feature=["state"])
    model = lgb.train(PARAMS, data, num_boost_round=ROUNDS)

    test = ~train
    y_test = df["y"].to_numpy()[test]
    mu_test = np.exp(model.predict(X[test], raw_score=True) + offset[test])
    uf = df[test].assign(y_hat=mu_test).groupby(["state", "ds"])[["y", "y_hat"]].sum()

    # Desvio de Poisson explicado no teste, contra um modelo só de taxa média.
    def deviance(y, mu):
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(y > 0, y * np.log(y / mu), 0.0)
        return 2 * (term - (y - mu)).sum()

    rate = df["y"][train].sum() / df["population"][train].sum()
    null_mu = rate * df["population"].to_numpy()[test]
    metrics = {
        "disease": disease,
        "deviance_explained_test": 1 - deviance(y_test, mu_test) / deviance(y_test, null_mu),
        "mae_municipio_test": float(np.abs(y_test - mu_test).mean()),
        "wape_municipio_test": float(np.abs(y_test - mu_test).sum() / y_test.sum() * 100),
        "wape_uf_test": float((uf["y"] - uf["y_hat"]).abs().sum() / uf["y"].sum() * 100),
        "bias_pct_test": float((mu_test.sum() / y_test.sum() - 1) * 100),
    }

    sample = X[test].sample(min(SHAP_SAMPLE, int(test.sum())), random_state=0)
    values = shap.TreeExplainer(model).shap_values(sample)
    mean_abs = pd.Series(np.abs(values).mean(axis=0), index=X.columns)
    grouped = mean_abs.groupby(base_variable).sum()
    importance = [
        {"disease": disease, "variable": v, "label": LABELS[v], "mean_abs_shap": float(s),
         "share_pct": float(s / grouped.sum() * 100)}
        for v, s in grouped.sort_values(ascending=False).items()
    ]
    return importance, metrics


def main() -> None:
    panel = load_panel("municipio")
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    importance, metrics = [], []

    totals = panel.groupby("disease", observed=True)["y"].sum()
    for disease in totals[totals >= MIN_TOTAL_CASES].index:
        start = time.time()
        rows, m = fit_disease(str(disease), panel[panel["disease"] == disease].copy())
        importance += rows
        metrics.append(m)
        print(f"{disease}: {time.time() - start:.0f}s, dev. explicada (teste) {m['deviance_explained_test']:.2f}, "
              f"WAPE UF {m['wape_uf_test']:.1f}%, top: {rows[0]['label']}", flush=True)

    pd.DataFrame(importance).to_csv(STUDY_DIR / "lgbm_importance.csv", index=False)
    pd.DataFrame(metrics).to_csv(STUDY_DIR / "lgbm_metrics.csv", index=False)


if __name__ == "__main__":
    main()
