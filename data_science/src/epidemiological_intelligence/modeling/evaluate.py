import numpy as np
import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

def calculate_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
) -> dict:
    mae = mean_absolute_error(
        y_true,
        y_pred
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred
        )
    )

    if y_true.nunique() > 1:
        r2 = r2_score(
            y_true,
            y_pred
        )
    else:
        r2 = np.nan

    total_cases = y_true.sum()

    if total_cases > 0:
        wape = (
            np.abs(
                y_true - y_pred
            ).sum()
            / total_cases
        ) * 100
    else:
        wape = np.nan

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2)
        if not np.isnan(r2)
        else np.nan,
        "wape_pct": float(wape)
        if not np.isnan(wape)
        else np.nan,
    }
    
def compare_models(
    y_true,
    base_pred,
    final_pred,
) -> dict:

    base_metrics = calculate_metrics(
        y_true,
        base_pred
    )

    final_metrics = calculate_metrics(
        y_true,
        final_pred
    )

    mae_improvement = (
        (
            base_metrics["mae"]
            - final_metrics["mae"]
        )
        / base_metrics["mae"]
    ) * 100

    rmse_improvement = (
        (
            base_metrics["rmse"]
            - final_metrics["rmse"]
        )
        / base_metrics["rmse"]
    ) * 100

    return {
        "base": base_metrics,
        "final": final_metrics,
        "mae_improvement_pct": float(
            mae_improvement
        ),
        "rmse_improvement_pct": float(
            rmse_improvement
        ),
    }
    
def metrics_by_municipality(
    test_df: pd.DataFrame,
    prediction_column: str,
) -> pd.DataFrame:

    results = []

    for municipality, group in (
        test_df.groupby("municipality")
    ):

        metrics = calculate_metrics(
            group["cases"],
            group[prediction_column]
        )

        results.append({
            "municipality": municipality,
            "n": len(group),
            "mean_cases": group["cases"].mean(),
            **metrics,
        })

    return pd.DataFrame(results)