import json

import pandas as pd
from google.api_core.exceptions import GoogleAPIError
from langchain_core.documents import Document

from epidemiological_agent.tools import llm_tools


def _mock_max_date(monkeypatch, date_str):
    monkeypatch.setattr(
        llm_tools,
        "get_max_reference_date",
        lambda: pd.Timestamp(date_str),
    )


def _raise(exc):
    def _fn(*args, **kwargs):
        raise exc

    return _fn


def test_epidemiological_data_tool_returns_message_when_empty(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "query_epidemiological_data",
        lambda **kwargs: pd.DataFrame(),
    )

    result = llm_tools.epidemiological_data_tool.invoke(
        {"disease": "ASMA"}
    )

    assert result == "No data found for the requested filters."


def test_epidemiological_data_tool_returns_records_as_json(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "reference_date": pd.Timestamp("2024-01-01"),
                "disease": "ASMA",
                "municipality": "PORTO ALEGRE",
                "cases": 10,
            }
        ]
    )
    monkeypatch.setattr(
        llm_tools,
        "query_epidemiological_data",
        lambda **kwargs: df,
    )

    result = llm_tools.epidemiological_data_tool.invoke(
        {"disease": "ASMA", "municipality": "PORTO ALEGRE"}
    )

    parsed = json.loads(result)
    assert parsed == [
        {
            "reference_date": "2024-01-01T00:00:00.000",
            "disease": "ASMA",
            "municipality": "PORTO ALEGRE",
            "cases": 10,
        }
    ]


def test_epidemiological_data_tool_rejects_future_start_date(monkeypatch):
    _mock_max_date(monkeypatch, "2025-06-30")
    monkeypatch.setattr(
        llm_tools,
        "query_epidemiological_data",
        _raise(AssertionError("BigQuery should not be queried")),
    )

    result = llm_tools.epidemiological_data_tool.invoke(
        {"disease": "ASMA", "start_date": "2026-01-01"}
    )

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["error_type"] == "date_out_of_range"
    assert "2025-06-30" in parsed["message"]


def test_epidemiological_data_tool_allows_start_date_within_range(monkeypatch):
    _mock_max_date(monkeypatch, "2025-06-30")
    df = pd.DataFrame(
        [
            {
                "reference_date": pd.Timestamp("2025-01-01"),
                "disease": "ASMA",
                "municipality": "PORTO ALEGRE",
                "cases": 3,
            }
        ]
    )
    monkeypatch.setattr(
        llm_tools,
        "query_epidemiological_data",
        lambda **kwargs: df,
    )

    result = llm_tools.epidemiological_data_tool.invoke(
        {"disease": "ASMA", "start_date": "2025-01-01"}
    )

    parsed = json.loads(result)
    assert parsed[0]["cases"] == 3


_FAKE_ALERTS = pd.DataFrame(
    [
        {
            "origin_type": "fechado", "origin_month": pd.Timestamp("2026-03-01"), "disease": "ASMA",
            "state": "RS", "municipality_name": None, "target_month": pd.Timestamp("2026-04-01"),
            "horizon": 1, "probability": 0.71, "alert": True, "threshold": 120.0, "cases_p10": 100.0,
            "cases_p50": 130.0, "cases_p90": 160.0, "observed_cases": 140.0,
        }
    ]
)


def test_outbreak_alerts_tool_returns_state_level_rows(monkeypatch):
    seen = {}

    def fake_latest(filters, limit):
        seen["filters"] = filters
        return _FAKE_ALERTS

    monkeypatch.setattr(llm_tools.alert_queries, "latest_alerts", fake_latest)

    result = llm_tools.outbreak_alerts_tool.invoke({"disease": "ASMA", "state": "RS"})

    parsed = json.loads(result)
    assert parsed[0]["probability"] == 0.71
    assert seen["filters"].level == "uf"
    assert seen["filters"].origin_type == "fechado"
    assert seen["filters"].only_alerts is True


def test_outbreak_alerts_tool_resolves_municipality_to_code(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        llm_tools.gold_queries,
        "municipalities",
        lambda state=None: pd.DataFrame(
            [{"municipality_code": "431490", "municipality_name": "Porto Alegre", "state": "RS"}]
        ),
    )

    def fake_latest(filters, limit):
        seen["filters"] = filters
        return _FAKE_ALERTS

    monkeypatch.setattr(llm_tools.alert_queries, "latest_alerts", fake_latest)

    llm_tools.outbreak_alerts_tool.invoke({"municipality": "porto alegre", "state": "RS"})

    assert seen["filters"].level == "municipio"
    assert seen["filters"].municipality_code == "431490"


def test_outbreak_alerts_tool_asks_for_state_on_homonyms(monkeypatch):
    monkeypatch.setattr(
        llm_tools.gold_queries,
        "municipalities",
        lambda state=None: pd.DataFrame(
            [
                {"municipality_code": "431690", "municipality_name": "Santa Maria", "state": "RS"},
                {"municipality_code": "241250", "municipality_name": "Santa Maria", "state": "RN"},
            ]
        ),
    )

    result = llm_tools.outbreak_alerts_tool.invoke({"municipality": "Santa Maria"})

    assert "RN, RS" in result


def test_outbreak_alerts_tool_handles_query_failure(monkeypatch):
    monkeypatch.setattr(llm_tools.alert_queries, "latest_alerts", _raise(GoogleAPIError("boom")))

    parsed = json.loads(llm_tools.outbreak_alerts_tool.invoke({"disease": "ASMA"}))

    assert parsed["status"] == "error"
    assert parsed["error_type"] == "alerts_unavailable"


def test_alert_model_info_tool_reports_missing_run(monkeypatch):
    monkeypatch.setattr(llm_tools.alert_queries, "model_info", lambda: None)

    parsed = json.loads(llm_tools.alert_model_info_tool.invoke({}))

    assert parsed["error_type"] == "artifact_not_found"


def test_alert_model_info_tool_returns_info_as_json(monkeypatch):
    info = {"model_version": "chronos2-clima-cross-v1", "cutoffs": {"uf": 0.3}}
    monkeypatch.setattr(llm_tools.alert_queries, "model_info", lambda: info)

    assert json.loads(llm_tools.alert_model_info_tool.invoke({})) == info


def test_climate_summary_tool_returns_summary_as_json(monkeypatch):
    summary = {
        "precipitation_sum_mm": {"avg": 12.5, "min": 0.0, "max": 80.0},
        "temperature_avg_c": {"avg": 21.0, "min": 10.0, "max": 32.0},
    }
    monkeypatch.setattr(
        llm_tools,
        "get_climate_summary",
        lambda **kwargs: summary,
    )

    result = llm_tools.climate_summary_tool.invoke(
        {"disease": "ASMA", "municipality": "PORTO ALEGRE"}
    )

    assert json.loads(result) == summary


def test_climate_summary_tool_rejects_future_start_date(monkeypatch):
    _mock_max_date(monkeypatch, "2025-06-30")
    monkeypatch.setattr(
        llm_tools,
        "get_climate_summary",
        _raise(AssertionError("BigQuery should not be queried")),
    )

    result = llm_tools.climate_summary_tool.invoke(
        {"disease": "ASMA", "start_date": "2026-01-01"}
    )

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["error_type"] == "date_out_of_range"
    assert "2025-06-30" in parsed["message"]


def test_climate_summary_tool_handles_query_failure(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "get_climate_summary",
        _raise(Exception("query failed")),
    )

    result = llm_tools.climate_summary_tool.invoke({"disease": "ASMA"})

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["source"] == "bigquery"
    assert parsed["error_type"] == "query_failed"


def test_total_cases_tool_returns_total_as_string(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "get_total_cases",
        lambda **kwargs: 42,
    )

    result = llm_tools.total_cases_tool.invoke(
        {"disease": "ASMA", "municipality": "PORTO ALEGRE"}
    )

    assert result == "42"


def test_total_cases_tool_rejects_future_start_date(monkeypatch):
    _mock_max_date(monkeypatch, "2025-06-30")
    monkeypatch.setattr(
        llm_tools,
        "get_total_cases",
        _raise(AssertionError("BigQuery should not be queried")),
    )

    result = llm_tools.total_cases_tool.invoke(
        {"disease": "ASMA", "start_date": "2026-01-01"}
    )

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["error_type"] == "date_out_of_range"
    assert "2025-06-30" in parsed["message"]


def test_total_cases_tool_handles_query_failure(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "get_total_cases",
        _raise(Exception("query failed")),
    )

    result = llm_tools.total_cases_tool.invoke(
        {"disease": "ASMA"}
    )

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["source"] == "bigquery"
    assert parsed["error_type"] == "query_failed"


def test_retrieve_knowledge_tool_joins_documents(monkeypatch):
    docs = [
        Document(page_content="Trecho sobre binomial negativa."),
        Document(page_content="Trecho sobre vazamento de dados."),
    ]
    monkeypatch.setattr(
        llm_tools,
        "search_knowledge",
        lambda query, k=2: docs,
    )

    result = llm_tools.retrieve_knowledge_tool.invoke(
        {"query": "binomial negativa"}
    )

    assert "Trecho sobre binomial negativa." in result
    assert "Trecho sobre vazamento de dados." in result
    assert "---" in result


def test_retrieve_knowledge_tool_returns_not_found_when_no_docs(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "search_knowledge",
        lambda query, k=2: [],
    )

    result = llm_tools.retrieve_knowledge_tool.invoke(
        {"query": "algo inexistente"}
    )

    parsed = json.loads(result)
    assert parsed["status"] == "not_found"


def test_retrieve_knowledge_tool_handles_retrieval_failure(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "search_knowledge",
        _raise(Exception("chroma unavailable")),
    )

    result = llm_tools.retrieve_knowledge_tool.invoke(
        {"query": "binomial negativa"}
    )

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["source"] == "rag"
    assert parsed["error_type"] == "retrieval_failed"


def test_resolve_disease_ignores_accents_case_and_partial_names():
    assert llm_tools.resolve_disease("ACIDENTE POR ESCORPIÃO") == ("ACIDENTE POR ESCORPIÃO", None)
    assert llm_tools.resolve_disease("acidentes por escorpiao") == ("ACIDENTE POR ESCORPIÃO", None)
    assert llm_tools.resolve_disease("Escorpião") == ("ACIDENTE POR ESCORPIÃO", None)
    assert llm_tools.resolve_disease("infarto") == ("INFARTO AGUDO DO MIOCÁRDIO", None)
    assert llm_tools.resolve_disease("insuficiencia cardiaca") == ("INSUFICIÊNCIA CARDÍACA", None)


def test_resolve_disease_reports_ambiguous_and_unknown_names():
    name, problem = llm_tools.resolve_disease("bronquite")
    assert name is None and "BRONQUITE AGUDA" in problem and "BRONQUITE CRÔNICA" in problem

    name, problem = llm_tools.resolve_disease("dengue")
    assert name is None and "Unknown disease" in problem


def test_total_cases_tool_queries_the_resolved_disease_name(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_tools, "get_max_reference_date", lambda: None)
    monkeypatch.setattr(llm_tools, "get_total_cases", lambda **kwargs: calls.append(kwargs) or 44974)

    result = llm_tools.total_cases_tool.invoke({"disease": "escorpião", "state": "MG"})

    assert result == "44974"
    assert calls[0]["disease"] == "ACIDENTE POR ESCORPIÃO"
