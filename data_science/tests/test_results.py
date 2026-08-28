import io
import json

import pandas as pd

from epidemiological_intelligence.artifacts import results


DISEASE = "LEPTOSPIROSE"
SLUG = "leptospirose"
VERSION = "v1"


def test_save_metrics_uses_expected_path_and_content(fake_storage):
    metrics = {"mae": 1.0, "rmse": 2.0}

    results.save_metrics(disease=DISEASE, version=VERSION, metrics=metrics)

    path = f"modeling/{SLUG}/{VERSION}/metrics.json"
    assert path in fake_storage.objects
    assert json.loads(fake_storage.objects[path]) == metrics


def test_save_predictions_uses_expected_path_and_parquet_content(fake_storage):
    df = pd.DataFrame({"municipality": ["A", "B"], "cases": [1, 2]})

    results.save_predictions(disease=DISEASE, version=VERSION, predictions=df)

    path = f"modeling/{SLUG}/{VERSION}/predictions.parquet"
    assert path in fake_storage.objects

    roundtrip = pd.read_parquet(io.BytesIO(fake_storage.objects[path]))
    pd.testing.assert_frame_equal(roundtrip, df)


def test_save_municipality_metrics_uses_expected_path_and_parquet_content(fake_storage):
    df = pd.DataFrame({"municipality": ["A"], "mae": [1.0]})

    results.save_municipality_metrics(
        disease=DISEASE,
        version=VERSION,
        municipality_metrics=df,
    )

    path = f"modeling/{SLUG}/{VERSION}/municipality_metrics.parquet"
    assert path in fake_storage.objects

    roundtrip = pd.read_parquet(io.BytesIO(fake_storage.objects[path]))
    pd.testing.assert_frame_equal(roundtrip, df)


def test_save_metadata_uses_expected_path_and_content(fake_storage):
    metadata = {"disease": DISEASE, "model_version": VERSION}

    results.save_metadata(disease=DISEASE, version=VERSION, metadata=metadata)

    path = f"modeling/{SLUG}/{VERSION}/metadata.json"
    assert json.loads(fake_storage.objects[path]) == metadata


def test_save_latest_pointer_uses_expected_path_and_content(fake_storage):
    metadata = {
        "run_id": "20240101T000000Z",
        "trained_at": "2024-01-01T00:00:00+00:00",
    }

    results.save_latest_pointer(disease=DISEASE, version=VERSION, metadata=metadata)

    path = f"modeling/{SLUG}/latest.json"
    assert path in fake_storage.objects

    payload = json.loads(fake_storage.objects[path])
    assert payload["disease"] == DISEASE
    assert payload["version"] == VERSION
    assert payload["run_id"] == metadata["run_id"]
    assert payload["trained_at"] == metadata["trained_at"]
    assert payload["path"] == f"modeling/{SLUG}/{VERSION}"
