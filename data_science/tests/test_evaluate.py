import math

import pandas as pd
import pytest

from epidemiological_intelligence.modeling.evaluate import (
    calculate_metrics,
    compare_models,
    metrics_by_municipality,
)


def test_calculate_metrics_perfect_prediction():
    y_true = pd.Series([10, 20, 30, 40])
    y_pred = pd.Series([10, 20, 30, 40])

    metrics = calculate_metrics(y_true, y_pred)

    assert metrics["mae"] == pytest.approx(0.0)
    assert metrics["rmse"] == pytest.approx(0.0)
    assert metrics["r2"] == pytest.approx(1.0)
    assert metrics["wape_pct"] == pytest.approx(0.0)


def test_calculate_metrics_known_errors():
    # errors: 0, 0, 0, +1 -> hand-computed expected values below
    y_true = pd.Series([1, 2, 3, 4])
    y_pred = pd.Series([1, 2, 3, 5])

    metrics = calculate_metrics(y_true, y_pred)

    assert metrics["mae"] == pytest.approx(0.25)
    assert metrics["rmse"] == pytest.approx(0.5)
    assert metrics["r2"] == pytest.approx(0.8)
    assert metrics["wape_pct"] == pytest.approx(10.0)


def test_calculate_metrics_r2_is_nan_when_y_true_has_no_variance():
    y_true = pd.Series([10, 10, 10])
    y_pred = pd.Series([9, 10, 11])

    metrics = calculate_metrics(y_true, y_pred)

    assert math.isnan(metrics["r2"])


def test_calculate_metrics_wape_is_nan_when_total_cases_is_zero():
    y_true = pd.Series([0, 0, 0])
    y_pred = pd.Series([1, 0, 0])

    metrics = calculate_metrics(y_true, y_pred)

    assert math.isnan(metrics["wape_pct"])


def test_compare_models_improvement_percentages():
    y_true = pd.Series([1, 2, 3, 4])
    base_pred = pd.Series([0, 0, 0, 0])
    final_pred = pd.Series([1, 2, 3, 5])

    result = compare_models(y_true, base_pred, final_pred)

    expected_base_mae = 2.5
    expected_final_mae = 0.25
    expected_base_rmse = math.sqrt((1 + 4 + 9 + 16) / 4)
    expected_final_rmse = 0.5

    assert result["base"]["mae"] == pytest.approx(expected_base_mae)
    assert result["final"]["mae"] == pytest.approx(expected_final_mae)
    assert result["mae_improvement_pct"] == pytest.approx(
        (expected_base_mae - expected_final_mae) / expected_base_mae * 100
    )
    assert result["rmse_improvement_pct"] == pytest.approx(
        (expected_base_rmse - expected_final_rmse) / expected_base_rmse * 100
    )


def test_metrics_by_municipality_groups_correctly():
    test_df = pd.DataFrame(
        {
            "municipality": ["A", "A", "B", "B"],
            "cases": [10, 20, 5, 5],
            "prediction": [10, 20, 5, 15],
        }
    )

    result = metrics_by_municipality(test_df, prediction_column="prediction").set_index(
        "municipality"
    )

    assert result.loc["A", "n"] == 2
    assert result.loc["A", "mean_cases"] == pytest.approx(15.0)
    assert result.loc["A", "mae"] == pytest.approx(0.0)

    assert result.loc["B", "n"] == 2
    assert result.loc["B", "mean_cases"] == pytest.approx(5.0)
    assert result.loc["B", "mae"] == pytest.approx(5.0)
