import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from epidemiological_agent.api.app import app
from google.api_core.exceptions import NotFound

from epidemiological_agent.api.routers import data as data_router
from epidemiological_agent.api.rate_limit import chat_rate_limit
from epidemiological_agent.tools import alert_queries, gold_queries
from epidemiological_agent.tools.gold_queries import GoldFilters


@pytest.fixture
def client():
    return TestClient(app)


# Gold falso: Porto Alegre e Caxias (RS), Florianópolis (SC); Santa
# Maria existe no RS e no RN (homônimos, códigos diferentes).
FAKE_GOLD = pd.DataFrame(
    {
        "reference_date": pd.to_datetime(
            ["2024-01-01", "2024-02-01", "2023-01-01", "2023-02-01", "2024-01-01", "2024-01-01"]
        ),
        "disease": ["ASMA", "ASMA", "LEPTOSPIROSE", "LEPTOSPIROSE", "ASMA", "ASMA"],
        "municipality_code": ["431490", "430510", "431490", "420540", "431690", "241250"],
        "municipality": ["PORTO ALEGRE", "CAXIAS DO SUL", "PORTO ALEGRE", "FLORIANOPOLIS", "SANTA MARIA", "SANTA MARIA"],
        "municipality_name": ["Porto Alegre", "Caxias do Sul", "Porto Alegre", "Florianópolis", "Santa Maria", "Santa Maria"],
        "state": ["RS", "RS", "RS", "SC", "RS", "RN"],
        "cases": [10, 5, 20, 8, 3, 0],
    }
)

FAKE_DIM = pd.DataFrame(
    {
        "municipality_code": ["431490", "430510", "420540", "431690", "241250"],
        "municipality_name": ["Porto Alegre", "Caxias do Sul", "Florianópolis", "Santa Maria", "Santa Maria"],
        "state": ["RS", "RS", "SC", "RS", "RN"],
        "latitude": [-30.03, -29.17, -27.59, -29.68, -5.85],
        "longitude": [-51.23, -51.18, -48.55, -53.81, -35.73],
    }
)


def _apply(filters: GoldFilters) -> pd.DataFrame:
    """Mesma semântica de gold_queries.where_clause, em pandas."""

    df = FAKE_GOLD
    if filters.diseases:
        df = df[df["disease"].isin({d.upper() for d in filters.diseases})]
    if filters.state:
        df = df[df["state"] == filters.state.upper()]
    if filters.municipality_code:
        df = df[df["municipality_code"] == filters.municipality_code]
    if filters.municipality:
        df = df[df["municipality"] == gold_queries.normalize_name(filters.municipality)]
    if filters.start_date:
        df = df[df["reference_date"] >= pd.Timestamp(filters.start_date)]
    if filters.end_date:
        df = df[df["reference_date"] <= pd.Timestamp(filters.end_date)]
    return df


@pytest.fixture(autouse=True)
def _fake_gold_queries(monkeypatch):
    monkeypatch.setattr(
        gold_queries, "monthly_cases",
        lambda f: _apply(f).groupby("reference_date", as_index=False)["cases"].sum(),
    )
    monkeypatch.setattr(
        gold_queries, "cases_by_disease",
        lambda f: _apply(f).groupby("disease", as_index=False).agg(
            cases=("cases", "sum"),
            municipality_count=("municipality_code", lambda s: s[_apply(f).loc[s.index, "cases"] > 0].nunique()),
        ),
    )
    monkeypatch.setattr(
        gold_queries, "municipality_count",
        lambda f: _apply(f).loc[lambda d: d["cases"] > 0, "municipality_code"].nunique(),
    )
    monkeypatch.setattr(
        gold_queries, "cases_by_state",
        lambda f: _apply(f).groupby("state", as_index=False)["cases"].sum(),
    )
    monkeypatch.setattr(
        gold_queries, "cases_by_municipality",
        lambda f: _apply(f)
        .groupby(["municipality_code", "municipality_name", "state"], as_index=False)["cases"].sum()
        .merge(FAKE_DIM[["municipality_code", "latitude", "longitude"]], on="municipality_code", how="left"),
    )
    monkeypatch.setattr(gold_queries, "diseases", lambda: sorted(FAKE_GOLD["disease"].unique()))
    monkeypatch.setattr(
        gold_queries, "municipalities",
        lambda state=None: FAKE_DIM[FAKE_DIM["state"] == state.upper()] if state else FAKE_DIM,
    )


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    # Limiter é singleton de módulo: sem reset, requisições de um teste
    # contariam nos seguintes.
    chat_rate_limit.reset()


def _raise(exc):
    def _fn(*args, **kwargs):
        raise exc

    return _fn


# ---------------------------------------------------------------------
# /overview
# ---------------------------------------------------------------------


def test_overview_aggregates_gold_table(client):
    response = client.get("/overview")

    assert response.status_code == 200
    body = response.json()

    assert body["metrics"]["totalCases"] == 46
    # Santa Maria/RN tem 0 casos: não conta. Santa Maria/RS conta à parte.
    assert body["metrics"]["municipalityCount"] == 4
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

    assert body["metrics"]["totalCases"] == 18
    assert {s["disease"] for s in body["diseaseDistribution"]} == {"ASMA"}


def test_overview_filters_by_state(client):
    response = client.get("/overview", params={"state": "sc"})

    assert response.status_code == 200
    assert response.json()["metrics"]["totalCases"] == 8


def test_overview_filters_by_date_range(client):
    response = client.get(
        "/overview",
        params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["metrics"]["totalCases"] == 18
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


def test_geo_country_lists_all_27_states(client):
    response = client.get("/geo/country")

    assert response.status_code == 200
    body = response.json()

    by_id = {area["id"]: area for area in body}
    assert len(by_id) == 27
    assert by_id["RS"]["hasData"] is True
    assert by_id["RS"]["cases"] == 38
    assert by_id["SC"]["cases"] == 8
    assert by_id["SP"]["hasData"] is False
    assert by_id["SP"]["cases"] == 0


def test_geo_state_groups_by_municipality_code_with_coordinates(client):
    response = client.get("/geo/state", params={"state": "RS"})

    assert response.status_code == 200
    body = response.json()

    by_id = {area["id"]: area for area in body}
    assert by_id["431490"]["name"] == "Porto Alegre"
    assert by_id["431490"]["cases"] == 30
    assert by_id["431490"]["latitude"] == -30.03
    assert by_id["430510"]["cases"] == 5
    # Santa Maria/RN não aparece no mapa do RS.
    assert "241250" not in by_id
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
    assert by_id["RS"]["cases"] == 18


def test_geo_state_filters_by_date_range(client):
    response = client.get(
        "/geo/state",
        params={"state": "RS", "start_date": "2024-01-01", "end_date": "2024-12-31"},
    )

    assert response.status_code == 200
    body = response.json()

    by_id = {area["id"]: area for area in body}
    assert by_id["431490"]["cases"] == 10
    assert by_id["430510"]["cases"] == 5


# ---------------------------------------------------------------------
# /studies
# ---------------------------------------------------------------------


def test_studies_adds_alert_summary_per_disease(monkeypatch, client):
    monkeypatch.setattr(
        alert_queries,
        "alerts_by_disease",
        lambda origin_type: pd.DataFrame([{"disease": "ASMA", "state_alerts": 2, "max_probability": 0.8}]),
    )

    response = client.get("/studies")

    assert response.status_code == 200
    by_disease = {s["disease"]: s for s in response.json()}
    assert by_disease["ASMA"]["statesInAlert"] == 2
    assert by_disease["ASMA"]["maxAlertProbability"] == 0.8
    assert by_disease["LEPTOSPIROSE"]["statesInAlert"] is None
    assert by_disease["ASMA"]["totalCases"] == 18
    assert by_disease["ASMA"]["municipalityCount"] == 3


def test_studies_works_before_the_first_alert_run(monkeypatch, client):
    monkeypatch.setattr(alert_queries, "alerts_by_disease", _raise(NotFound("outbreak_alerts")))

    response = client.get("/studies")

    assert response.status_code == 200
    assert all(s["statesInAlert"] is None for s in response.json())


# ---------------------------------------------------------------------
# /alerts
# ---------------------------------------------------------------------


_FAKE_ALERT_ROWS = pd.DataFrame(
    [
        {
            "run_id": pd.Timestamp("2026-10-10", tz="UTC"), "model_version": "chronos2-clima-cross-v1",
            "origin_type": "fechado", "origin_month": pd.Timestamp("2026-03-01"), "level": "municipio",
            "disease": "ASMA", "source": "SIH", "state": "RS", "municipality_code": "431490",
            "municipality_name": "Porto Alegre", "target_month": pd.Timestamp("2026-04-01"), "horizon": 1,
            "threshold": 120.4, "cases_p10": 100.0, "cases_p50": 130.0, "cases_p90": 160.0,
            "probability": 0.71, "cutoff": 0.2, "alert": True, "observed_cases": float("nan"),
            "target_provisional": pd.NA,
        }
    ]
)


def test_alerts_forwards_filters_and_serializes_rows(monkeypatch, client):
    seen = {}

    def fake_latest(filters, limit):
        seen["filters"], seen["limit"] = filters, limit
        return _FAKE_ALERT_ROWS

    monkeypatch.setattr(alert_queries, "latest_alerts", fake_latest)

    response = client.get(
        "/alerts",
        params={"level": "municipio", "origin_type": "fechado", "state": "rs", "only_alerts": True, "limit": 20},
    )

    assert response.status_code == 200
    row = response.json()[0]
    assert row["municipalityName"] == "Porto Alegre"
    assert row["originMonth"] == "2026-03-01"
    assert row["targetMonth"] == "2026-04-01"
    assert row["observedCases"] is None
    assert row["targetProvisional"] is None
    assert seen["filters"].level == "municipio"
    assert seen["filters"].state == "rs"
    assert seen["filters"].only_alerts is True
    assert seen["limit"] == 20


def test_alerts_rejects_unknown_level(client):
    assert client.get("/alerts", params={"level": "bairro"}).status_code == 422
    assert client.get("/alerts", params={"origin_type": "amanha"}).status_code == 422


def test_alert_states_names_each_state(monkeypatch, client):
    monkeypatch.setattr(
        alert_queries,
        "state_summary",
        lambda origin_type, horizon, disease: pd.DataFrame(
            [{"state": "RS", "max_probability": 0.6, "state_alerts": 1, "municipality_alerts": 4}]
        ),
    )

    body = client.get("/alerts/states", params={"origin_type": "provisorio", "horizon": 2}).json()

    assert body == [
        {"state": "RS", "name": "Rio Grande do Sul", "maxProbability": 0.6, "stateAlerts": 1, "municipalityAlerts": 4}
    ]


def test_alert_model_404_before_the_first_run(monkeypatch, client):
    monkeypatch.setattr(alert_queries, "model_info", lambda: None)

    assert client.get("/alerts/model").status_code == 404


def test_alert_model_returns_metrics(monkeypatch, client):
    metrics = {"precision": 0.56, "recall": 0.55, "f1": 0.55, "auc_pr": 0.59, "auc_roc": 0.83, "brier": 0.12,
               "test_predictions": 23328, "outbreak_pct": 20.7}
    monkeypatch.setattr(
        alert_queries,
        "model_info",
        lambda: {
            "run_id": "2026-10-10T00:00:00+00:00",
            "model_version": "chronos2-clima-cross-v1",
            "model": {"name": "Chronos-2 (Amazon), zero-shot", "covariates": ["temperature_avg_c"], "horizons": [1, 2, 3]},
            "cutoffs": {"uf": 0.3, "municipio": 0.2},
            "test_metrics": {"uf": metrics, "municipio": metrics},
            "origins": [{"origin_type": "fechado", "disease": "ASMA", "origin_month": "2026-03-01"}],
        },
    )

    body = client.get("/alerts/model").json()

    assert body["modelVersion"] == "chronos2-clima-cross-v1"
    assert body["testMetrics"]["uf"]["aucRoc"] == 0.83
    assert body["origins"][0]["originMonth"] == "2026-03-01"


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

    def fake_query(**kwargs):
        captured.update(kwargs)
        return df

    monkeypatch.setattr(data_router, "query_epidemiological_data", fake_query)

    response = client.get(
        "/data",
        params={"disease": "ASMA", "state": "RS", "municipality_code": "431490", "start_date": "2024-01-01"},
    )

    assert response.status_code == 200
    body = response.json()

    assert captured == {
        "disease": "ASMA",
        "municipality": None,
        "start_date": "2024-01-01",
        "end_date": None,
        "state": "RS",
        "municipality_code": "431490",
    }
    assert body[0]["cases"] == 10.0
    assert body[1]["cases"] is None
    assert body[1]["precipitationSumMm"] is None
    # Sem state/municipality_code no DataFrame: campos opcionais nulos.
    assert body[0]["state"] is None


# ---------------------------------------------------------------------
# /municipalities
# ---------------------------------------------------------------------


def test_municipalities_returns_code_name_and_state(client):
    response = client.get("/municipalities")

    assert response.status_code == 200
    body = response.json()
    assert {"code": "431690", "name": "Santa Maria", "state": "RS"} in body
    assert {"code": "241250", "name": "Santa Maria", "state": "RN"} in body


def test_municipalities_filters_by_state(client):
    response = client.get("/municipalities", params={"state": "sc"})

    assert response.status_code == 200
    assert response.json() == [{"code": "420540", "name": "Florianópolis", "state": "SC"}]


# ---------------------------------------------------------------------
# Filtros SQL (gold_queries.where_clause)
# ---------------------------------------------------------------------


def test_where_clause_is_parametrized_and_normalizes_names():
    where, parameters = gold_queries.where_clause(
        GoldFilters(diseases=("asma",), state="rs", municipality="São Paulo", start_date="2024-01-01")
    )

    assert "@diseases" in where and "@state" in where and "@municipality" in where
    values = {p.name: getattr(p, "value", None) or getattr(p, "values", None) for p in parameters}
    assert values["diseases"] == ["ASMA"]
    assert values["state"] == "RS"
    assert values["municipality"] == "SAO PAULO"
    # Nada de valor do usuário interpolado no SQL.
    assert "Paulo" not in where and "RS" not in where


def test_where_clause_without_filters_matches_everything():
    where, parameters = gold_queries.where_clause(GoldFilters())

    assert where == "TRUE"
    assert parameters == []
