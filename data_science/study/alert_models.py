"""
Parte B, modelos de alerta com atributos (um modelo por nível, todas as
doenças juntas). Treina com alvos de 2020-2022 e grava a probabilidade
de surto para os alvos de 2023 (calibração do corte) e 2024-2025
(teste):

- persistencia: alerta se a origem está em surto;
- sazonal_ingenuo: alerta se o mesmo mês do ano anterior foi surto;
- glm_nb: GLM binomial negativo da contagem -> P(passar do limite);
- lgbm_poisson: LightGBM da contagem -> P(passar do limite) com a
  mesma dispersão binomial negativa estimada no treino;
- lgbm_classificador: LightGBM que prevê o surto (0/1) direto.

Importância (OUTPUT_DIR/alert/importance.csv): SHAP médio nos dois
LightGBM; |z| dos coeficientes no GLM.

Uso: python alert_models.py
"""

import time

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
import statsmodels.api as sm
from scipy import stats

from alert_features import CATEGORICAL, FEATURES, base_variable, build, with_log_population
from common import ALERT_DIR, CALIBRATION_TARGETS, LABELS, TRAIN_TARGETS, save_alert

SHAP_SAMPLE = 30_000
PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "verbose": -1,
}
ROUNDS = 500


def exceed_nb(mu: np.ndarray, alpha: float, threshold: np.ndarray, min_cases: np.ndarray) -> np.ndarray:
    """P(Y > limite e Y >= mínimo), Y ~ binomial negativa(média mu, dispersão alpha)."""

    cut = np.maximum(np.floor(threshold) + 1, min_cases)  # menor contagem que é surto
    n = 1 / alpha
    return stats.nbinom.sf(cut - 1, n, n / (n + mu))


def nb_alpha(y: np.ndarray, mu: np.ndarray) -> float:
    aux = ((y - mu) ** 2 - y) / mu
    return max(float((aux * mu).sum() / (mu * mu).sum()), 1e-6)


def output(table: pd.DataFrame, level: str, probability: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "level": level,
            "series_id": table["series_id"].to_numpy(),
            "disease": table["disease"].astype(str).to_numpy(),
            "state": table["state"].astype(str).to_numpy(),
            "ds": table["ds"].to_numpy(),
            "horizon": table["horizon"].to_numpy(),
            "probability": probability,
        }
    )


def importance_rows(model: str, level: str, values: pd.Series) -> list[dict]:
    grouped = values.groupby(base_variable).sum()
    return [
        {"model": model, "level": level, "variable": v, "label": LABELS.get(v, v), "importance": float(s),
         "share_pct": float(s / grouped.sum() * 100)}
        for v, s in grouped.sort_values(ascending=False).items()
    ]


def shap_importance(model, X: pd.DataFrame) -> pd.Series:
    sample = X.sample(min(SHAP_SAMPLE, len(X)), random_state=0)
    values = shap.TreeExplainer(model).shap_values(sample)
    if isinstance(values, list):  # versões antigas: uma matriz por classe
        values = values[-1]
    return pd.Series(np.abs(values).mean(axis=0), index=X.columns)


def glm_design(X: pd.DataFrame, stats_: dict | None = None) -> tuple[np.ndarray, list[str], dict]:
    numeric = [c for c in FEATURES if c not in CATEGORICAL and c not in ("horizon", "target_month")]
    data = X[numeric].copy()
    for column in [c for c in numeric if c.startswith(("y_", "threshold", "channel"))]:
        data[column] = np.log1p(data[column].clip(lower=0))
    stats_ = stats_ or {c: (data[c].mean(), data[c].std() or 1.0) for c in numeric}
    for column in numeric:
        mean, sd = stats_[column]
        data[column] = ((data[column] - mean) / sd).fillna(0.0)
    dummies = pd.get_dummies(
        X[["disease", "state"]].astype(str).assign(target_month=X["target_month"].astype(str), horizon=X["horizon"].astype(str)),
        drop_first=True,
        dtype=float,
    )
    if "columns" in stats_:
        dummies = dummies.reindex(columns=stats_["columns"], fill_value=0.0)
    else:
        stats_["columns"] = list(dummies.columns)
    matrix = np.column_stack(
        [np.ones(len(X)), data.to_numpy(dtype=float, na_value=0.0), dummies.to_numpy(dtype=float)]
    )
    return matrix, ["const", *numeric, *dummies.columns], stats_


def run_level(level: str) -> list[dict]:
    start = time.time()
    table = with_log_population(build(level))
    train = (table["ds"] <= TRAIN_TARGETS[1]).to_numpy()
    scored = (table["ds"] >= CALIBRATION_TARGETS[0]).to_numpy()
    print(f"{level}: {len(table)} linhas ({train.sum()} treino, {scored.sum()} avaliação)", flush=True)

    X = table[FEATURES]
    y = table["y"].to_numpy(dtype=float)
    label = table["outbreak"].to_numpy()
    threshold, min_cases = table["threshold"].to_numpy(), table["min_cases"].to_numpy()
    out = table[scored]
    importance: list[dict] = []

    save_alert(output(out, level, out["outbreak_origin"].to_numpy(dtype=float)), f"persistencia_{level}")
    # Comparar o ano anterior com o limite do alvo não serve: com 5 anos,
    # um valor do próprio canal fica no máximo 1,79 DP acima da média.
    save_alert(output(out, level, out["outbreak_same_month_1y"].to_numpy(dtype=float)), f"sazonal_ingenuo_{level}")

    # GLM binomial negativo (offset: log população).
    design, names, stats_ = glm_design(X[train])
    offset = table["log_population"].to_numpy()
    poisson = sm.GLM(y[train], design, family=sm.families.Poisson(), offset=offset[train]).fit(maxiter=100)
    alpha = nb_alpha(y[train], poisson.mu)
    glm = sm.GLM(y[train], design, family=sm.families.NegativeBinomial(alpha=alpha), offset=offset[train]).fit(
        start_params=poisson.params, maxiter=100
    )
    design_scored, *_ = glm_design(X[scored], stats_)
    mu = np.exp(design_scored @ glm.params + offset[scored])
    save_alert(output(out, level, exceed_nb(mu, alpha, threshold[scored], min_cases[scored])), f"glm_nb_{level}")
    z = pd.Series(np.abs(glm.tvalues), index=names)
    z = z[[n for n in names if n in FEATURES]]
    importance += importance_rows("glm_nb", level, z)
    print(f"  glm_nb ok ({time.time() - start:.0f}s, alpha {alpha:.2f})", flush=True)

    # LightGBM da contagem.
    data = lgb.Dataset(X[train], y[train], init_score=offset[train], categorical_feature=CATEGORICAL)
    counts = lgb.train({**PARAMS, "objective": "poisson"}, data, num_boost_round=ROUNDS)
    mu_train = np.exp(counts.predict(X[train], raw_score=True) + offset[train])
    alpha_lgbm = nb_alpha(y[train], mu_train)
    mu = np.exp(counts.predict(X[scored], raw_score=True) + offset[scored])
    save_alert(
        output(out, level, exceed_nb(mu, alpha_lgbm, threshold[scored], min_cases[scored])), f"lgbm_poisson_{level}"
    )
    importance += importance_rows("lgbm_poisson", level, shap_importance(counts, X[scored]))
    print(f"  lgbm_poisson ok ({time.time() - start:.0f}s)", flush=True)

    # LightGBM classificador.
    data = lgb.Dataset(X[train], label[train], categorical_feature=CATEGORICAL)
    classifier = lgb.train({**PARAMS, "objective": "binary"}, data, num_boost_round=ROUNDS)
    save_alert(output(out, level, classifier.predict(X[scored])), f"lgbm_classificador_{level}")
    importance += importance_rows("lgbm_classificador", level, shap_importance(classifier, X[scored]))
    print(f"  lgbm_classificador ok ({time.time() - start:.0f}s)", flush=True)

    return importance


def main() -> None:
    importance = []
    for level in ("uf", "municipio"):
        importance += run_level(level)
    pd.DataFrame(importance).to_csv(ALERT_DIR / "importance.csv", index=False)


if __name__ == "__main__":
    main()
