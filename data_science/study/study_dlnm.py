"""
Parte A1: DLNM (modelo de defasagem distribuída não linear), regressão
binomial negativa por doença, no painel município × mês.

log E[casos] = log(população)                      (offset: modela taxa)
             + cb(temperatura, lag 0-3) + cb(chuva, lag 0-3)
             + covariáveis de ambiente (padronizadas)
             + UF + mês do ano + tendência (spline do tempo)

cb = base cruzada: spline cúbica no valor (3 gl) × polinômio de grau 2
na defasagem. O efeito do clima é medido contra o padrão sazonal da UF:
um mês mais quente/chuvoso que o normal, não o verão em si.

Treina em 2015-2023 e mede o erro fora da amostra em 2024-2025.
Saídas em OUTPUT_DIR/study/: dlnm_curves.csv (risco relativo acumulado
nas 4 defasagens, contra a mediana), dlnm_lags.csv (risco no percentil
95 por defasagem), dlnm_covariates.csv (razão de taxas por 1 desvio
padrão) e dlnm_metrics.csv.
"""

import time

import numpy as np
import pandas as pd
import statsmodels.api as sm

from common import COVARIATES, LABELS, OUTPUT_DIR, load_panel

DLNM_VARIABLES = ["temperature_avg_c", "precipitation_sum_mm"]
LAGS = [0, 1, 2, 3]
TRAIN_END = pd.Timestamp("2023-12-01")
# Oropouche: 44 casos em 11 anos, não sustenta um modelo.
MIN_TOTAL_CASES = 1000

STUDY_DIR = OUTPUT_DIR / "study"


class NaturalSpline:
    """
    Spline cúbica natural (linear além dos nós da borda), base de
    Hastie, Tibshirani e Friedman (ESL, eq. 5.4-5.5): df = nós - 1.
    """

    def __init__(self, values: np.ndarray, df: int):
        self.knots = np.quantile(values, np.linspace(0.05, 0.95, df + 1))
        self.scale = self.knots[-1] - self.knots[0]

    def transform(self, x: np.ndarray) -> np.ndarray:
        k = (self.knots - self.knots[0]) / self.scale
        x = (np.asarray(x, dtype=float) - self.knots[0]) / self.scale

        def d(j):
            return (np.clip(x - k[j], 0, None) ** 3 - np.clip(x - k[-1], 0, None) ** 3) / (k[-1] - k[j])

        return np.column_stack([x] + [d(j) - d(len(k) - 2) for j in range(len(k) - 2)])


class CrossBasis:
    """Spline no valor (nós nos quantis do treino) × polinômio na defasagem."""

    def __init__(self, values: np.ndarray, df: int = 3):
        self.spline = NaturalSpline(values, df)
        lags = np.array(LAGS, dtype=float) / max(LAGS)
        self.lag_basis = np.column_stack([np.ones_like(lags), lags, lags**2])  # (n_lags, 3)

    def value_basis(self, x: np.ndarray) -> np.ndarray:
        return self.spline.transform(x)

    def transform(self, lagged: np.ndarray) -> np.ndarray:
        """lagged: (n, n_lags) -> (n, value_df * lag_df), coluna = (valor j, lag k)."""

        out = 0
        for index in range(lagged.shape[1]):
            out = out + np.einsum("nj,k->njk", self.value_basis(lagged[:, index]), self.lag_basis[index])
        return out.reshape(len(lagged), -1)

    def cumulative_vector(self, x: np.ndarray, reference: float) -> np.ndarray:
        """Contraste (x vs referência) somado nas defasagens, na ordem das colunas."""

        diff = self.value_basis(x) - self.value_basis(np.array([reference]))
        return np.einsum("nj,k->njk", diff, self.lag_basis.sum(axis=0)).reshape(len(x), -1)

    def lag_vector(self, x: float, reference: float) -> np.ndarray:
        diff = (self.value_basis(np.array([x])) - self.value_basis(np.array([reference])))[0]
        return np.stack([np.outer(diff, self.lag_basis[i]).ravel() for i in range(len(LAGS))])


def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["municipality_code", "ds"])
    grouped = df.groupby("municipality_code")
    for variable in DLNM_VARIABLES:
        for lag in LAGS:
            df[f"{variable}_l{lag}"] = grouped[variable].shift(lag)
    return df.dropna(subset=[f"{v}_l{max(LAGS)}" for v in DLNM_VARIABLES])


def covariate_matrix(df: pd.DataFrame, stats: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Covariáveis padronizadas (z); nulo -> média do treino + indicador."""

    stats = stats or {c: (df[c].mean(), df[c].std()) for c in COVARIATES}
    out = {}
    for column in COVARIATES:
        mean, sd = stats[column]
        out[column] = ((df[column] - mean) / sd).fillna(0.0)
        if column.startswith("snis_"):
            out[f"{column}_missing"] = df[column].isna().astype(float)
    return pd.DataFrame(out, index=df.index), stats


def fixed_effects(df: pd.DataFrame, trend_design=None):
    time_index = ((df["ds"].dt.year - 2015) * 12 + df["ds"].dt.month).to_numpy(dtype=float)
    if trend_design is None:
        # Tendência de longo prazo: ~1 grau de liberdade por ano de treino.
        trend_design = NaturalSpline(time_index, df=9)
        trend_design.last = time_index.max()
    # Fora do treino a tendência fica no último valor, sem extrapolar.
    trend = trend_design.transform(np.minimum(time_index, trend_design.last))
    dummies = pd.get_dummies(df[["state"]].assign(month=df["ds"].dt.month.astype(str)), drop_first=True, dtype=float)
    return np.column_stack([trend, dummies.to_numpy()]), trend_design, list(dummies.columns)


def design(df: pd.DataFrame, bases: dict, stats=None, trend_design=None, dummy_columns=None):
    blocks, names = [np.ones((len(df), 1))], ["const"]
    for variable in DLNM_VARIABLES:
        lagged = df[[f"{variable}_l{lag}" for lag in LAGS]].to_numpy()
        cb = bases[variable].transform(lagged)
        blocks.append(cb)
        names += [f"cb_{variable}_{i}" for i in range(cb.shape[1])]
    covariates, stats = covariate_matrix(df, stats)
    blocks.append(covariates.to_numpy())
    names += list(covariates.columns)
    fe, trend_design, columns = fixed_effects(df, trend_design)
    if dummy_columns is not None and columns != dummy_columns:
        # Teste com UFs/meses na mesma ordem do treino.
        fe_df = pd.DataFrame(fe[:, -len(columns):], columns=columns).reindex(columns=dummy_columns, fill_value=0.0)
        fe = np.column_stack([fe[:, : fe.shape[1] - len(columns)], fe_df.to_numpy()])
        columns = dummy_columns
    blocks.append(fe)
    names += [f"fe_{i}" for i in range(fe.shape[1])]
    return np.column_stack(blocks), names, stats, trend_design, columns


def nb_alpha(y: np.ndarray, mu: np.ndarray) -> float:
    """Dispersão da binomial negativa (regressão auxiliar de Cameron-Trivedi)."""

    aux = ((y - mu) ** 2 - y) / mu
    return max(float((aux * mu).sum() / (mu * mu).sum()), 1e-6)


def fit_disease(disease: str, df: pd.DataFrame) -> dict:
    train, test = df[df["ds"] <= TRAIN_END], df[df["ds"] > TRAIN_END]
    bases = {
        v: CrossBasis(train[[f"{v}_l{lag}" for lag in LAGS]].to_numpy().ravel()) for v in DLNM_VARIABLES
    }
    X, names, stats, trend_design, dummy_columns = design(train, bases)
    offset = np.log(train["population"].to_numpy())
    y = train["y"].to_numpy(dtype=float)

    poisson = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit(maxiter=100)
    alpha = nb_alpha(y, poisson.mu)
    model = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=offset).fit(
        start_params=poisson.params, maxiter=100
    )
    params, cov = model.params, model.cov_params()
    index = {name: i for i, name in enumerate(names)}

    curves, lags_rows = [], []
    for variable in DLNM_VARIABLES:
        cols = [index[n] for n in names if n.startswith(f"cb_{variable}_")]
        theta, v = params[cols], cov[np.ix_(cols, cols)]
        values = train[f"{variable}_l0"]
        reference = float(values.median())
        grid = np.linspace(values.quantile(0.01), values.quantile(0.99), 40)
        a = bases[variable].cumulative_vector(grid, reference)
        log_rr, se = a @ theta, np.sqrt(np.einsum("ij,jk,ik->i", a, v, a))
        curves += [
            {"disease": disease, "variable": variable, "x": x, "reference": reference,
             "rr": np.exp(l), "rr_low": np.exp(l - 1.96 * s), "rr_high": np.exp(l + 1.96 * s)}
            for x, l, s in zip(grid, log_rr, se)
        ]
        high = float(values.quantile(0.95))
        lv = bases[variable].lag_vector(high, reference)
        log_rr, se = lv @ theta, np.sqrt(np.einsum("ij,jk,ik->i", lv, v, lv))
        lags_rows += [
            {"disease": disease, "variable": variable, "lag": lag, "x": high, "reference": reference,
             "rr": np.exp(l), "rr_low": np.exp(l - 1.96 * s), "rr_high": np.exp(l + 1.96 * s)}
            for lag, l, s in zip(LAGS, log_rr, se)
        ]

    covariates = []
    for column in COVARIATES:
        i = index[column]
        b, s = params[i], np.sqrt(cov[i, i])
        covariates.append(
            {"disease": disease, "variable": column, "label": LABELS[column], "irr": np.exp(b),
             "irr_low": np.exp(b - 1.96 * s), "irr_high": np.exp(b + 1.96 * s), "z": b / s}
        )

    X_test, *_ = design(test, bases, stats, trend_design, dummy_columns)
    mu_test = np.exp(X_test @ params + np.log(test["population"].to_numpy()))
    y_test = test["y"].to_numpy(dtype=float)
    uf = test.assign(y_hat=mu_test).groupby(["state", "ds"])[["y", "y_hat"]].sum()
    metrics = {
        "disease": disease,
        "alpha": alpha,
        "deviance_explained_train": 1 - model.deviance / model.null_deviance,
        "mae_municipio_test": float(np.abs(y_test - mu_test).mean()),
        "wape_municipio_test": float(np.abs(y_test - mu_test).sum() / y_test.sum() * 100),
        "wape_uf_test": float((uf["y"] - uf["y_hat"]).abs().sum() / uf["y"].sum() * 100),
        "bias_pct_test": float((mu_test.sum() / y_test.sum() - 1) * 100),
    }
    return {"curves": curves, "lags": lags_rows, "covariates": covariates, "metrics": metrics}


def main() -> None:
    panel = load_panel("municipio")
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    results = {"curves": [], "lags": [], "covariates": [], "metrics": []}

    totals = panel.groupby("disease", observed=True)["y"].sum()
    for disease in totals[totals >= MIN_TOTAL_CASES].index:
        start = time.time()
        df = add_lags(panel[panel["disease"] == disease].copy())
        result = fit_disease(str(disease), df)
        for key in results:
            results[key] += result[key] if isinstance(result[key], list) else [result[key]]
        m = result["metrics"]
        print(f"{disease}: {time.time() - start:.0f}s, dev. explicada {m['deviance_explained_train']:.2f}, "
              f"WAPE UF {m['wape_uf_test']:.1f}%", flush=True)

    for key, rows in results.items():
        pd.DataFrame(rows).to_csv(STUDY_DIR / f"dlnm_{key}.csv", index=False)


if __name__ == "__main__":
    main()
