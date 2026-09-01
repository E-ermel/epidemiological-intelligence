import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from epidemiological_agent.api.app import app
from epidemiological_agent.api.routers import data as data_router
from epidemiological_agent.api.routers import geography as geography_router
from epidemiological_agent.api.routers import models as models_router
from epidemiological_agent.api.routers import overview as overview_router
from epidemiological_agent.api import gold_data
from epidemiological_agent.api import model_metadata_batch


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_gold_df():
    return pd.DataFrame(
        {
            "reference_date": [
                "2024-01-01",
                "2024-02-01",
                "2023-01-01",
                "2023-02-01",
            ],
            "disease": ["ASMA", "ASMA", "LEPTOSPIROSE", "LEPTOSPIROSE"],
            "municipality": [
                "PORTO ALEGRE",
                "CAXIAS DO SUL",
                "PORTO ALEGRE",
                "PELOTAS",
            ],
            "cases": [10, 5, 20, 8],
            "precipitation_sum_mm": [1.0, 2.0, None, 3.0],
            "precipitation_max_observation_mm": [1.0] * 4,
            "temperature_avg_c": [20.0] * 4,
            "dew_point_avg_c": [10.0] * 4,
            "relative_humidity_avg_pct": [60.0] * 4,
            "atmospheric_pressure_avg_mb": [1010.0] * 4,
            "wind_speed_avg_ms": [3.0] * 4,
            "wind_gust_max_ms": [8.0] * 4,
        }
    )


@pytest.fixture(autouse=True)
def _patch_gold_query(monkeypatch, fake_gold_df):
    monkeypatch.setattr(
        gold_data,
        "query_epidemiological_data",
        lambda *args, **kwargs: fake_gold_df.copy(),
    )


# ---------------------------------------------------------------------
# /overview
# ---------------------------------------------------------------------


def test_overview_aggregates_gold_table(client):
    response = client.get("/overview")

    assert response.status_code == 200
    body = response.json()

    assert body["metrics"]["totalCases"] == 43
    assert body["metrics"]["municipalityCount"] == 3
    assert body["metrics"]["diseaseCount"] == 2
    assert body["metrics"]["periodStart"] == "2023-01-01"
    assert body["metrics"]["periodEnd"] == "2024-02-01"
    assert len(body["caseCurve"]) == 4
    assert {slice_["disease"] for slice_ in body["diseaseDistribution"]} == {
        "ASMA",
        "LEPTOSPIROSE",
    }


def test_overview_filters_by_disease(client):
    response = client.get("/overview", params={"disease": "ASMA"})

    assert response.status_code == 200
    body = response.json()

    assert body["metrics"]["totalCases"] == 15
    assert {s["disease"] for s in body["diseaseDistribution"]} == {"ASMA"}


def test_overview_filters_by_date_range(client):
    response = client.get(
        "/overview",
        params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["metrics"]["totalCases"] == 15
    assert body["metrics"]["periodStart"] == "2024-01-01"
    assert body["metrics"]["periodEnd"] == "2024-02-01"


def test_overview_returns_empty_metrics_when_filter_matches_nothing(client):
    response = client.get("/overview", params={"disease": "DENGUE"})

    assert response.status_code == 200
    body = response.json()

    assert body["metrics"]["totalCases"] == 0
    assert body["caseCurve"] == []
    assert body["diseaseDistribution"] == []


# ---------------------------------------------------------------------
# /geo/{level}
# ---------------------------------------------------------------------


def test_geo_country_only_rs_has_data(client):
    response = client.get("/geo/country")

    assert response.status_code == 200
    body = response.json()

    by_id = {area["id"]: area for area in body}
    assert by_id["RS"]["hasData"] is True
    assert by_id["RS"]["cases"] == 43
    assert by_id["SC"]["hasData"] is False
    assert by_id["SC"]["cases"] == 0


def test_geo_state_rs_groups_by_municipality(client):
    response = client.get("/geo/state", params={"state": "RS"})

    assert response.status_code == 200
    body = response.json()

    by_id = {area["id"]: area for area in body}
    assert by_id["PORTO ALEGRE"]["cases"] == 30
    assert by_id["CAXIAS DO SUL"]["cases"] == 5
    assert by_id["PELOTAS"]["cases"] == 8
    assert all(area["hasData"] for area in body)


def test_geo_unknown_level_returns_empty_list(client):
    response = client.get("/geo/planet")

    assert response.status_code == 200
    assert response.json() == []


def test_geo_country_filters_by_disease(client):
    response = client.get("/geo/country", params={"disease": "ASMA"})

    assert response.status_code == 200
    body = response.json()

    by_id = {area["id"]: area for area in body}
    assert by_id["RS"]["cases"] == 15


def test_geo_state_filters_by_date_range(client):
    response = client.get(
        "/geo/state",
        params={"state": "RS", "start_date": "2024-01-01", "end_date": "2024-12-31"},
    )

    assert response.status_code == 200
    body = response.json()

    by_id = {area["id"]: area for area in body}
    assert by_id["PORTO ALEGRE"]["cases"] == 10
    assert by_id["CAXIAS DO SUL"]["cases"] == 5
    assert "PELOTAS" not in by_id


# ---------------------------------------------------------------------
# /studies
# ---------------------------------------------------------------------


def test_studies_marks_missing_model_as_none(monkeypatch, client):
    def fake_get_model_metadata(disease):
        if disease == "LEPTOSPIROSE":
            raise FileNotFoundError()
        return {"model_version": "v3"}

    monkeypatch.setattr(
        model_metadata_batch, "get_model_metadata", fake_get_model_metadata
    )

    response = client.get("/studies")

    assert response.status_code == 200
    by_disease = {s["disease"]: s for s in response.json()}
    assert by_disease["ASMA"]["activeModelVersion"] == "v3"
    assert by_disease["LEPTOSPIROSE"]["activeModelVersion"] is None
    assert by_disease["ASMA"]["totalCases"] == 15


# ---------------------------------------------------------------------
# /models
# ---------------------------------------------------------------------


_FAKE_METADATA = {
    "disease": "ASMA",
    "model_version": "v3",
    "run_id": "20240711T090000Z",
    "trained_at": "2024-07-11T09:00:00+00:00",
    "model_type": "Negative Binomial",
    "features": ["relative_humidity_avg_pct"],
    "training_period": {"start": "2019-01-01", "end": "2023-12-01"},
    "test_period": {"start": "2024-01-01", "end": "2024-06-01"},
    "metrics": {
        "base": {"mae": 5.0, "rmse": 6.0, "r2": 0.4, "wape_pct": 20.0},
        "final": {"mae": 3.8, "rmse": 5.1, "r2": 0.71, "wape_pct": 14.2},
        "mae_improvement_pct": 24.0,
        "rmse_improvement_pct": 15.0,
    },
}


def test_models_skips_diseases_without_a_trained_model(monkeypatch, client):
    def fake_get_model_metadata(disease):
        if disease != "ASMA":
            raise FileNotFoundError()
        return _FAKE_METADATA

    monkeypatch.setattr(
        model_metadata_batch, "get_model_metadata", fake_get_model_metadata
    )

    response = client.get("/models")

    assert response.status_code == 200
    body = response.json()
    assert [m["disease"] for m in body] == ["ASMA"]
    # ModelMetadataResponse mirrors metadata.json verbatim (snake_case),
    # unlike the other new schemas which camelCase for the frontend.
    assert body[0]["model_version"] == "v3"


# ---------------------------------------------------------------------
# /models/{disease}/predictions
# ---------------------------------------------------------------------


@pytest.fixture
def fake_predictions_df():
    return pd.DataFrame(
        {
            "reference_date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "municipality": ["Porto Alegre", "Caxias do Sul"],
            "cases": [10.0, 5.0],
            "base_prediction": [8.0, 4.0],
            "final_prediction": [9.5, 4.5],
        }
    )


def test_predictions_returns_observed_and_predicted(
    monkeypatch, client, fake_predictions_df
):
    monkeypatch.setattr(
        models_router, "get_predictions", lambda disease: fake_predictions_df.copy()
    )

    response = client.get("/models/ASMA/predictions")

    assert response.status_code == 200
    body = response.json()
    assert body[0] == {
        "referenceDate": "2024-01-01",
        "municipality": "Porto Alegre",
        "observedCases": 10.0,
        "predictedCases": 9.5,
    }


def test_predictions_filters_by_municipality_case_insensitively(
    monkeypatch, client, fake_predictions_df
):
    monkeypatch.setattr(
        models_router, "get_predictions", lambda disease: fake_predictions_df.copy()
    )

    response = client.get(
        "/models/ASMA/predictions", params={"municipality": "porto alegre"}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["municipality"] == "Porto Alegre"


def test_predictions_404_when_disease_has_no_model(monkeypatch, client):
    monkeypatch.setattr(
        models_router,
        "get_predictions",
        lambda disease: (_ for _ in ()).throw(FileNotFoundError()),
    )

    response = client.get("/models/LEPTOSPIROSE/predictions")

    assert response.status_code == 404


# ---------------------------------------------------------------------
# POST /models/{disease}/retrain
# ---------------------------------------------------------------------


def test_retrain_starts_job_for_known_disease(monkeypatch, client):
    monkeypatch.setattr(
        models_router, "trigger_retrain", lambda disease: f"operations/{disease}-123"
    )

    response = client.post("/models/ASMA/retrain")

    assert response.status_code == 200
    assert response.json() == {
        "status": "started",
        "executionName": "operations/ASMA-123",
    }


def test_retrain_404_for_unknown_disease(client):
    response = client.post("/models/DENGUE/retrain")

    assert response.status_code == 404


def test_retrain_502_when_job_trigger_fails(monkeypatch, client):
    from google.api_core.exceptions import GoogleAPICallError

    def fake_trigger(disease):
        raise GoogleAPICallError("boom")

    monkeypatch.setattr(models_router, "trigger_retrain", fake_trigger)

    response = client.post("/models/ASMA/retrain")

    assert response.status_code == 502


# ---------------------------------------------------------------------
# GET /models/retrain/status (polled while a retrain is in progress)
# ---------------------------------------------------------------------


def test_retrain_status_running_has_no_completion_time(monkeypatch, client):
    from google.cloud.run_v2.types import Execution
    from google.protobuf.timestamp_pb2 import Timestamp

    execution = Execution(
        task_count=1,
        running_count=1,
        log_uri="https://console.cloud.google.com/logs/x",
        start_time=Timestamp(seconds=1_700_000_000),
    )
    monkeypatch.setattr(models_router, "get_execution_status", lambda name: execution)

    response = client.get(
        "/models/retrain/status",
        params={"execution": "projects/p/locations/r/jobs/j/executions/e"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["logUri"] == "https://console.cloud.google.com/logs/x"
    assert body["startTime"] is not None
    assert body["completionTime"] is None


def test_retrain_status_reports_succeeded(monkeypatch, client):
    from google.cloud.run_v2.types import Condition, Execution
    from google.protobuf.timestamp_pb2 import Timestamp

    execution = Execution(
        task_count=1,
        succeeded_count=1,
        conditions=[
            Condition(type_="Completed", state=Condition.State.CONDITION_SUCCEEDED)
        ],
        completion_time=Timestamp(seconds=1_700_000_500),
    )
    monkeypatch.setattr(models_router, "get_execution_status", lambda name: execution)

    response = client.get(
        "/models/retrain/status",
        params={"execution": "projects/p/locations/r/jobs/j/executions/e"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_retrain_status_succeeded_invalidates_model_metadata_cache(monkeypatch, client):
    """
    Regression test: a finished retrain must drop the cached
    get_model_metadata() results, otherwise /models and /studies keep
    reporting "no model" for up to 5 minutes after training actually
    completed -- see model_tools.invalidate_model_metadata_cache.
    """
    from google.cloud.run_v2.types import Condition, Execution

    execution = Execution(
        task_count=1,
        succeeded_count=1,
        conditions=[
            Condition(type_="Completed", state=Condition.State.CONDITION_SUCCEEDED)
        ],
    )
    monkeypatch.setattr(models_router, "get_execution_status", lambda name: execution)

    calls = []
    monkeypatch.setattr(
        models_router, "invalidate_model_metadata_cache", lambda: calls.append(True)
    )

    response = client.get(
        "/models/retrain/status",
        params={"execution": "projects/p/locations/r/jobs/j/executions/e"},
    )

    assert response.status_code == 200
    assert calls == [True]


def test_retrain_status_running_does_not_invalidate_cache(monkeypatch, client):
    from google.cloud.run_v2.types import Execution

    execution = Execution(task_count=1, running_count=1)
    monkeypatch.setattr(models_router, "get_execution_status", lambda name: execution)

    calls = []
    monkeypatch.setattr(
        models_router, "invalidate_model_metadata_cache", lambda: calls.append(True)
    )

    response = client.get(
        "/models/retrain/status",
        params={"execution": "projects/p/locations/r/jobs/j/executions/e"},
    )

    assert response.status_code == 200
    assert calls == []


def test_retrain_status_502_when_lookup_fails(monkeypatch, client):
    from google.api_core.exceptions import GoogleAPICallError

    def fake_get(name):
        raise GoogleAPICallError("boom")

    monkeypatch.setattr(models_router, "get_execution_status", fake_get)

    response = client.get(
        "/models/retrain/status",
        params={"execution": "projects/p/locations/r/jobs/j/executions/e"},
    )

    assert response.status_code == 502


# ---------------------------------------------------------------------
# POST /models/retrain (bulk -- every disease in one job execution)
# ---------------------------------------------------------------------


def test_retrain_all_starts_a_single_job_with_no_disease_filter(monkeypatch, client):
    calls = []

    def fake_trigger(disease=None):
        calls.append(disease)
        return "operations/all-123"

    monkeypatch.setattr(models_router, "trigger_retrain", fake_trigger)

    response = client.post("/models/retrain")

    assert response.status_code == 200
    assert response.json() == {
        "status": "started",
        "executionName": "operations/all-123",
    }
    assert calls == [None]


def test_retrain_all_502_when_job_trigger_fails(monkeypatch, client):
    from google.api_core.exceptions import GoogleAPICallError

    def fake_trigger(disease=None):
        raise GoogleAPICallError("boom")

    monkeypatch.setattr(models_router, "trigger_retrain", fake_trigger)

    response = client.post("/models/retrain")

    assert response.status_code == 502


# ---------------------------------------------------------------------
# /data
# ---------------------------------------------------------------------


def test_data_forwards_filters_and_nulls_out_nan(monkeypatch, client):
    df = pd.DataFrame(
        {
            "reference_date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "disease": ["ASMA", "ASMA"],
            "municipality": ["Porto Alegre", "Pelotas"],
            "cases": [10.0, math.nan],
            "precipitation_sum_mm": [1.0, math.nan],
            "precipitation_max_observation_mm": [1.0, 1.0],
            "temperature_avg_c": [20.0, 20.0],
            "dew_point_avg_c": [10.0, 10.0],
            "relative_humidity_avg_pct": [60.0, 60.0],
            "atmospheric_pressure_avg_mb": [1010.0, 1010.0],
            "wind_speed_avg_ms": [3.0, 3.0],
            "wind_gust_max_ms": [8.0, 8.0],
        }
    )

    captured = {}

    def fake_query(disease=None, municipality=None, start_date=None, end_date=None):
        captured.update(
            disease=disease,
            municipality=municipality,
            start_date=start_date,
            end_date=end_date,
        )
        return df

    monkeypatch.setattr(data_router, "query_epidemiological_data", fake_query)

    response = client.get(
        "/data", params={"disease": "ASMA", "start_date": "2024-01-01"}
    )

    assert response.status_code == 200
    body = response.json()

    assert captured == {
        "disease": "ASMA",
        "municipality": None,
        "start_date": "2024-01-01",
        "end_date": None,
    }
    assert body[0]["cases"] == 10.0
    assert body[1]["cases"] is None
    assert body[1]["precipitationSumMm"] is None


# ---------------------------------------------------------------------
# /municipalities
# ---------------------------------------------------------------------


def test_municipalities_returns_sorted_distinct_names(client):
    response = client.get("/municipalities")

    assert response.status_code == 200
    assert response.json() == ["CAXIAS DO SUL", "PELOTAS", "PORTO ALEGRE"]
