import pandas as pd
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from epidemiological_agent.graph import nodes
from epidemiological_agent.graph.graph import agent_graph
from epidemiological_agent.tools import llm_tools


def _raise(exc):
    def _fn(*args, **kwargs):
        raise exc

    return _fn


class _FakeLLM:
    # llm_with_tools is a pydantic model and rejects ad-hoc attribute
    # patching, so tests swap the whole nodes.llm_with_tools reference.
    def __init__(self, responses):
        self._responses = list(responses)

    def invoke(self, *args, **kwargs):
        return self._responses.pop(0)


def _fake_llm(responses):
    return _FakeLLM(responses)


def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def test_agent_answers_epidemiological_query_via_tool_call(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "reference_date": pd.Timestamp("2024-03-01"),
                "disease": "ASMA",
                "municipality": "PORTO ALEGRE",
                "cases": 12,
            }
        ]
    )
    monkeypatch.setattr(
        llm_tools, "query_epidemiological_data", lambda **kwargs: df
    )
    monkeypatch.setattr(
        nodes,
        "llm_with_tools",
        _fake_llm(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "epidemiological_data_tool",
                            "args": {
                                "disease": "ASMA",
                                "municipality": "PORTO ALEGRE",
                            },
                            "id": "call_1",
                        }
                    ],
                ),
                AIMessage(content="Em março de 2024 houve 12 casos de asma."),
            ]
        ),
    )

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Quantos casos de asma em março?")]},
        config=_thread_config("epi-query"),
    )

    assert result["messages"][-1].content == "Em março de 2024 houve 12 casos de asma."
    tool_message = result["messages"][-2]
    assert tool_message.name == "epidemiological_data_tool"
    assert "PORTO ALEGRE" in tool_message.content


def test_agent_answers_total_cases_question_via_tool_call(monkeypatch):
    monkeypatch.setattr(llm_tools, "get_total_cases", lambda **kwargs: 128)
    monkeypatch.setattr(
        nodes,
        "llm_with_tools",
        _fake_llm(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "total_cases_tool",
                            "args": {"disease": "ASMA"},
                            "id": "call_1",
                        }
                    ],
                ),
                AIMessage(content="Foram registrados 128 casos de asma."),
            ]
        ),
    )

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Quantos casos de asma tivemos ao todo?")]},
        config=_thread_config("total-cases"),
    )

    assert result["messages"][-1].content == "Foram registrados 128 casos de asma."
    tool_message = result["messages"][-2]
    assert tool_message.name == "total_cases_tool"
    assert tool_message.content == "128"


def test_agent_answers_alert_reliability_question_via_tool_call(monkeypatch):
    info = {"model_version": "chronos2-clima-cross-v1", "test_metrics": {"uf": {"precision": 0.56}}}
    monkeypatch.setattr(llm_tools.alert_queries, "model_info", lambda: info)
    monkeypatch.setattr(
        nodes,
        "llm_with_tools",
        _fake_llm(
            [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "alert_model_info_tool", "args": {}, "id": "call_1"}],
                ),
                AIMessage(content="Na UF, 56 de cada 100 alertas foram surtos."),
            ]
        ),
    )

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="O alerta é confiável?")]},
        config=_thread_config("alert-model"),
    )

    assert result["messages"][-1].content == "Na UF, 56 de cada 100 alertas foram surtos."
    tool_message = result["messages"][-2]
    assert tool_message.name == "alert_model_info_tool"
    assert "0.56" in tool_message.content


def test_agent_answers_outbreak_question_via_tool_call(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "origin_type": "fechado", "origin_month": pd.Timestamp("2026-07-01"), "disease": "LEPTOSPIROSE",
                "state": "RS", "municipality_name": None, "target_month": pd.Timestamp("2026-08-01"), "horizon": 1,
                "probability": 0.64, "alert": True, "threshold": 40.0, "cases_p10": 30.0, "cases_p50": 45.0,
                "cases_p90": 70.0, "observed_cases": None,
            }
        ]
    )
    monkeypatch.setattr(llm_tools.alert_queries, "latest_alerts", lambda filters, limit: df)
    monkeypatch.setattr(
        nodes,
        "llm_with_tools",
        _fake_llm(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "outbreak_alerts_tool",
                            "args": {"disease": "LEPTOSPIROSE", "state": "RS"},
                            "id": "call_1",
                        }
                    ],
                ),
                AIMessage(content="Há alerta de leptospirose no RS para agosto (64%)."),
            ]
        ),
    )

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Tem surto de leptospirose previsto no RS?")]},
        config=_thread_config("outbreak"),
    )

    assert result["messages"][-1].content == "Há alerta de leptospirose no RS para agosto (64%)."
    tool_message = result["messages"][-2]
    assert tool_message.name == "outbreak_alerts_tool"
    assert "0.64" in tool_message.content


def test_agent_routes_to_rag_tool_for_methodology_question(monkeypatch):
    docs = [Document(page_content="O modelo usa regressão binomial negativa.")]
    monkeypatch.setattr(llm_tools, "search_knowledge", lambda query, k=2: docs)
    monkeypatch.setattr(
        nodes,
        "llm_with_tools",
        _fake_llm(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "retrieve_knowledge_tool",
                            "args": {"query": "metodologia de modelagem"},
                            "id": "call_1",
                        }
                    ],
                ),
                AIMessage(
                    content="A metodologia usa regressão binomial negativa."
                ),
            ]
        ),
    )

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Qual metodologia foi usada nos modelos?")]},
        config=_thread_config("rag-methodology"),
    )

    assert result["messages"][-1].content == (
        "A metodologia usa regressão binomial negativa."
    )
    tool_message = result["messages"][-2]
    assert tool_message.name == "retrieve_knowledge_tool"
    assert "binomial negativa" in tool_message.content


def test_agent_recovers_after_tool_error(monkeypatch):
    monkeypatch.setattr(
        llm_tools, "get_total_cases", _raise(Exception("bigquery indisponível"))
    )
    monkeypatch.setattr(
        nodes,
        "llm_with_tools",
        _fake_llm(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "total_cases_tool",
                            "args": {"disease": "ASMA"},
                            "id": "call_1",
                        }
                    ],
                ),
                AIMessage(
                    content=(
                        "Não consegui consultar o total de casos agora, "
                        "tente novamente em instantes."
                    )
                ),
            ]
        ),
    )

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Quantos casos de asma tivemos?")]},
        config=_thread_config("tool-error"),
    )

    tool_message = result["messages"][-2]
    assert tool_message.name == "total_cases_tool"
    assert '"status": "error"' in tool_message.content
    assert '"error_type": "query_failed"' in tool_message.content

    final = result["messages"][-1]
    assert "Não consegui consultar" in final.content


def test_agent_answers_directly_without_tool_call(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "llm_with_tools",
        _fake_llm(
            [AIMessage(content="Olá! Como posso ajudar com dados epidemiológicos?")]
        ),
    )

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Oi, tudo bem?")]},
        config=_thread_config("greeting"),
    )

    assert result["messages"][-1].content == (
        "Olá! Como posso ajudar com dados epidemiológicos?"
    )
    assert len(result["messages"]) == 2
