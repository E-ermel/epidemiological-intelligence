from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from epidemiological_agent.graph.routing import should_continue


def test_should_continue_returns_tools_when_last_message_has_tool_calls():
    state = {
        "messages": [
            HumanMessage(content="Quantos casos de asma em Porto Alegre?"),
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
        ]
    }

    assert should_continue(state) == "tools"


def test_should_continue_returns_end_when_last_message_has_no_tool_calls():
    state = {
        "messages": [
            HumanMessage(content="Quantos casos de asma em Porto Alegre?"),
            AIMessage(content="Foram 42 casos em 2024."),
        ]
    }

    assert should_continue(state) == END


def test_should_continue_only_looks_at_last_message():
    state = {
        "messages": [
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
            AIMessage(content="Resposta final sem tool calls."),
        ]
    }

    assert should_continue(state) == END
