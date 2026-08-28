import re
from datetime import datetime, timezone

from epidemiological_intelligence.artifacts.metadata import build_model_metadata


def _sample_comparison():
    return {
        "base": {"mae": 5.0, "rmse": 6.0, "r2": 0.1, "wape_pct": 50.0},
        "final": {"mae": 3.0, "rmse": 4.0, "r2": 0.5, "wape_pct": 30.0},
        "mae_improvement_pct": 40.0,
        "rmse_improvement_pct": 33.3,
    }


def test_build_model_metadata_has_expected_structure():
    comparison = _sample_comparison()

    metadata = build_model_metadata(
        disease="LEPTOSPIROSE",
        version="v3",
        selected_features=[
            "precipitation_sum_mm_lag1",
            "relative_humidity_avg_pct_lag1",
        ],
        comparison=comparison,
        train_start="2019-01-01",
        train_end="2023-12-01",
        test_start="2024-01-01",
        test_end="2024-06-01",
    )

    assert metadata["disease"] == "LEPTOSPIROSE"
    assert metadata["model_version"] == "v3"
    assert metadata["model_type"] == "Negative Binomial"
    assert metadata["features"] == [
        "precipitation_sum_mm_lag1",
        "relative_humidity_avg_pct_lag1",
    ]
    assert metadata["training_period"] == {
        "start": "2019-01-01",
        "end": "2023-12-01",
    }
    assert metadata["test_period"] == {
        "start": "2024-01-01",
        "end": "2024-06-01",
    }
    assert metadata["metrics"] == comparison


def test_build_model_metadata_run_id_and_trained_at_format_and_consistency():
    metadata = build_model_metadata(
        disease="ASMA",
        version="v1",
        selected_features=[],
        comparison={},
        train_start="a",
        train_end="b",
        test_start="c",
        test_end="d",
    )

    # format only -- never assert an exact timestamp value
    assert re.fullmatch(r"\d{8}T\d{6}Z", metadata["run_id"])

    trained_at = datetime.fromisoformat(metadata["trained_at"])
    assert trained_at.tzinfo is not None

    # run_id must be trained_at expressed in the same compact UTC format
    assert (
        trained_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        == metadata["run_id"]
    )


def test_build_model_metadata_does_not_mutate_caller_features_list():
    features_input = ["a", "b"]

    metadata = build_model_metadata(
        disease="ASMA",
        version="v1",
        selected_features=features_input,
        comparison={},
        train_start="a",
        train_end="b",
        test_start="c",
        test_end="d",
    )

    metadata["features"].append("mutated")

    assert features_input == ["a", "b"]
