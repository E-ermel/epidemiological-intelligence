import json

import pandas as pd
from google.api_core.exceptions import GoogleAPIError
from langchain_core.documents import Document

from epidemiological_agent.tools import llm_tools


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


def test_model_metrics_tool_returns_metrics_as_json(monkeypatch):
    metrics = {"base": {"mae": 1.0}, "final": {"mae": 0.9}}
    monkeypatch.setattr(
        llm_tools,
        "get_model_metrics",
        lambda disease: metrics,
    )

    result = llm_tools.model_metrics_tool.invoke({"disease": "ASMA"})

    assert json.loads(result) == metrics


def test_model_metrics_tool_handles_file_not_found(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "get_model_metrics",
        _raise(FileNotFoundError()),
    )

    result = llm_tools.model_metrics_tool.invoke({"disease": "ASMA"})

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["source"] == "gcs"
    assert parsed["error_type"] == "artifact_not_found"


def test_model_metrics_tool_handles_google_api_error(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "get_model_metrics",
        _raise(GoogleAPIError("boom")),
    )

    result = llm_tools.model_metrics_tool.invoke({"disease": "ASMA"})

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["source"] == "gcs"
    assert parsed["error_type"] == "storage_unavailable"


def test_municipality_model_metrics_tool_filters_by_municipality(monkeypatch):
    df = pd.DataFrame(
        [
            {"municipality": "PORTO ALEGRE", "mae": 1.0},
            {"municipality": "CANOAS", "mae": 2.0},
        ]
    )
    monkeypatch.setattr(
        llm_tools,
        "get_municipality_metrics",
        lambda disease: df,
    )

    result = llm_tools.municipality_model_metrics_tool.invoke(
        {"disease": "ASMA", "municipality": "PORTO ALEGRE"}
    )

    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["municipality"] == "PORTO ALEGRE"


def test_municipality_model_metrics_tool_returns_message_when_not_found(monkeypatch):
    df = pd.DataFrame(
        [{"municipality": "CANOAS", "mae": 2.0}]
    )
    monkeypatch.setattr(
        llm_tools,
        "get_municipality_metrics",
        lambda disease: df,
    )

    result = llm_tools.municipality_model_metrics_tool.invoke(
        {"disease": "ASMA", "municipality": "PORTO ALEGRE"}
    )

    assert "No model metrics found" in result
    assert "PORTO ALEGRE" in result


def test_model_predictions_tool_filters_by_municipality(monkeypatch):
    df = pd.DataFrame(
        [
            {"municipality": "PORTO ALEGRE", "observed": 10, "predicted": 9},
            {"municipality": "CANOAS", "observed": 5, "predicted": 4},
        ]
    )
    monkeypatch.setattr(
        llm_tools,
        "get_predictions",
        lambda disease: df,
    )

    result = llm_tools.model_predictions_tool.invoke(
        {"disease": "ASMA", "municipality": "CANOAS"}
    )

    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["municipality"] == "CANOAS"


def test_model_predictions_tool_returns_message_when_empty(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "get_predictions",
        lambda disease: pd.DataFrame(),
    )

    result = llm_tools.model_predictions_tool.invoke(
        {"disease": "ASMA"}
    )

    assert result == "No predictions found."


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
