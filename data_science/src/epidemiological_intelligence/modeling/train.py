from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


@dataclass
class ModelMetrics:
    mae: float
    rmse: float
    r2: float
    wape_pct: float


@dataclass
class DiseaseModelResult:
    disease: str

    base_model: object
    final_model: object

    train_df: pd.DataFrame
    test_df: pd.DataFrame

    selected_features: list[str]

    base_predictions: pd.Series
    final_predictions: pd.Series

    base_metrics: ModelMetrics
    final_metrics: ModelMetrics

    mae_improvement_pct: float
    rmse_improvement_pct: float

    alpha: float
    converged: bool

    excluded_municipalities: list[str]


def _normalize_model_types(
    df: pd.DataFrame,
    features: list[str],
) -> pd.DataFrame:

    df = df.copy()

    df["cases"] = df["cases"].astype("float64")
    df["month"] = df["month"].astype("int64")
    df["municipality"] = df["municipality"].astype(str)

    for feature in features:
        df[feature] = df[feature].astype("float64")

    return df


def _calculate_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
) -> ModelMetrics:

    mae = mean_absolute_error(
        y_true,
        y_pred,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred,
        )
    )

    if y_true.nunique() > 1:
        r2 = r2_score(
            y_true,
            y_pred,
        )
    else:
        r2 = np.nan

    total_cases = y_true.sum()

    if total_cases > 0:
        wape = (
            np.abs(y_true - y_pred).sum()
            / total_cases
        ) * 100
    else:
        wape = np.nan

    return ModelMetrics(
        mae=float(mae),
        rmse=float(rmse),
        r2=float(r2) if not np.isnan(r2) else np.nan,
        wape_pct=float(wape) if not np.isnan(wape) else np.nan,
    )


def _get_unseen_municipalities(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> list[str]:

    train_cities = set(
        train_df["municipality"].unique()
    )

    test_cities = set(
        test_df["municipality"].unique()
    )

    return sorted(
        test_cities - train_cities
    )


def train_disease_model(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    disease: str,
    selected_features: list[str],
    maxiter: int = 500,
) -> DiseaseModelResult:

    required_cols = [
        "cases",
        "municipality",
        "month",
    ] + selected_features

    train = (
        train_df[
            train_df["disease"] == disease
        ]
        .dropna(
            subset=required_cols
        )
        .copy()
    )

    test = (
        test_df[
            test_df["disease"] == disease
        ]
        .dropna(
            subset=required_cols
        )
        .copy()
    )

    train = _normalize_model_types(
        train,
        selected_features,
    )

    test = _normalize_model_types(
        test,
        selected_features,
    )

    # C(municipality) não consegue prever uma categoria
    # que não existia durante o treinamento.
    excluded_municipalities = (
        _get_unseen_municipalities(
            train,
            test,
        )
    )

    if excluded_municipalities:
        test = test[
            ~test["municipality"].isin(
                excluded_municipalities
            )
        ].copy()

    if train.empty:
        raise ValueError(
            f"Nenhuma observação válida de treino para {disease}."
        )

    if test.empty:
        raise ValueError(
            f"Nenhuma observação válida de teste para {disease}."
        )

    base_formula = (
        "cases ~ "
        "C(municipality) + "
        "C(month)"
    )

    if selected_features:
        final_formula = (
            base_formula
            + " + "
            + " + ".join(
                selected_features
            )
        )
    else:
        final_formula = base_formula

    base_model = (
        smf
        .negativebinomial(
            formula=base_formula,
            data=train,
        )
        .fit(
            method="bfgs",
            maxiter=maxiter,
            disp=False,
        )
    )

    final_model = (
        smf
        .negativebinomial(
            formula=final_formula,
            data=train,
        )
        .fit(
            method="bfgs",
            maxiter=maxiter,
            disp=False,
        )
    )

    converged = bool(
        final_model
        .mle_retvals
        .get(
            "converged",
            False,
        )
    )

    # Mesmo comportamento validado nos notebooks:
    # tenta novamente com mais iterações.
    if not converged and maxiter < 1000:

        final_model = (
            smf
            .negativebinomial(
                formula=final_formula,
                data=train,
            )
            .fit(
                method="bfgs",
                maxiter=1000,
                disp=False,
            )
        )

        converged = bool(
            final_model
            .mle_retvals
            .get(
                "converged",
                False,
            )
        )

    base_predictions = (
        base_model.predict(
            test
        )
    )

    final_predictions = (
        final_model.predict(
            test
        )
    )

    base_metrics = _calculate_metrics(
        test["cases"],
        base_predictions,
    )

    final_metrics = _calculate_metrics(
        test["cases"],
        final_predictions,
    )

    mae_improvement_pct = (
        (
            base_metrics.mae
            - final_metrics.mae
        )
        / base_metrics.mae
        * 100
    )

    rmse_improvement_pct = (
        (
            base_metrics.rmse
            - final_metrics.rmse
        )
        / base_metrics.rmse
        * 100
    )

    alpha = float(
        final_model.params.get(
            "alpha",
            np.nan,
        )
    )

    return DiseaseModelResult(
        disease=disease,

        base_model=base_model,
        final_model=final_model,

        train_df=train,
        test_df=test,

        selected_features=selected_features,

        base_predictions=base_predictions,
        final_predictions=final_predictions,

        base_metrics=base_metrics,
        final_metrics=final_metrics,

        mae_improvement_pct=float(
            mae_improvement_pct
        ),

        rmse_improvement_pct=float(
            rmse_improvement_pct
        ),

        alpha=alpha,

        converged=converged,

        excluded_municipalities=(
            excluded_municipalities
        ),
    )