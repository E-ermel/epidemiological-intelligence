from types import SimpleNamespace

import pandas as pd
import pytest

from epidemiological_intelligence.pipeline.run_modeling import run_disease_pipeline


class _FakeModel:
    """Stands in for the fitted statsmodels result; only .predict() is used
    downstream (predict_models), so that's all it needs to implement."""

    def __init__(self, value):
        self._value = value

    def predict(self, df):
        return pd.Series(self._value, index=df.index)


def _fake_train_disease_model(
    *, train_df, test_df, disease, selected_features, maxiter=500
):
    return SimpleNamespace(
        base_model=_FakeModel(2.0),
        final_model=_FakeModel(3.0),
        test_df=test_df,
    )


@pytest.fixture(autouse=True)
def _mock_training(monkeypatch):
    # Fitting a real negative binomial GLM is slow, and its convergence
    # depends on the data, not on what this suite is testing. Everything
    # else in the pipeline (preparation, features, prediction, evaluation,
    # versioning, publishing) runs for real against fake_storage.
    monkeypatch.setattr(
        "epidemiological_intelligence.pipeline.run_modeling.train_disease_model",
        _fake_train_disease_model,
    )


def test_run_disease_pipeline_rejects_unknown_disease(sample_gold_df, fake_storage):
    with pytest.raises(ValueError):
        run_disease_pipeline(df=sample_gold_df, disease="DOENCA_INEXISTENTE")


def test_run_disease_pipeline_end_to_end(sample_gold_df, fake_storage):
    result = run_disease_pipeline(df=sample_gold_df, disease="LEPTOSPIROSE")

    assert result["disease"] == "LEPTOSPIROSE"
    assert result["version"] == "v1"
    assert not result["predictions"].empty
    assert "final_prediction" in result["predictions"].columns
    assert set(result["municipality_metrics"]["municipality"]) == {
        "MUNI_A",
        "MUNI_B",
    }

    prefix = "modeling/leptospirose/v1/"
    assert f"{prefix}metrics.json" in fake_storage.objects
    assert f"{prefix}predictions.parquet" in fake_storage.objects
    assert f"{prefix}municipality_metrics.parquet" in fake_storage.objects
    assert f"{prefix}metadata.json" in fake_storage.objects
    assert "modeling/leptospirose/latest.json" in fake_storage.objects


def test_run_disease_pipeline_uses_next_version_when_previous_versions_exist(
    sample_gold_df, fake_storage
):
    fake_storage.objects["modeling/leptospirose/v1/metadata.json"] = b"{}"

    result = run_disease_pipeline(df=sample_gold_df, disease="LEPTOSPIROSE")

    assert result["version"] == "v2"
    assert "modeling/leptospirose/v2/metrics.json" in fake_storage.objects


def test_run_disease_pipeline_publishes_artifacts_in_the_expected_order(
    sample_gold_df, fake_storage
):
    run_disease_pipeline(df=sample_gold_df, disease="LEPTOSPIROSE")

    prefix = "modeling/leptospirose/v1/"
    assert fake_storage.upload_order == [
        f"{prefix}metrics.json",
        f"{prefix}predictions.parquet",
        f"{prefix}municipality_metrics.parquet",
        f"{prefix}metadata.json",
        "modeling/leptospirose/latest.json",
    ]


def test_run_disease_pipeline_does_not_update_latest_when_an_artifact_fails_to_publish(
    sample_gold_df, fake_storage
):
    fake_storage.failing_paths.add("municipality_metrics.parquet")

    with pytest.raises(RuntimeError):
        run_disease_pipeline(df=sample_gold_df, disease="LEPTOSPIROSE")

    prefix = "modeling/leptospirose/v1/"

    # published before the failure
    assert f"{prefix}metrics.json" in fake_storage.objects
    assert f"{prefix}predictions.parquet" in fake_storage.objects

    # the failed artifact, and everything meant to come after it, must
    # never be published -- most importantly, latest.json
    assert f"{prefix}municipality_metrics.parquet" not in fake_storage.objects
    assert f"{prefix}metadata.json" not in fake_storage.objects
    assert "modeling/leptospirose/latest.json" not in fake_storage.objects
