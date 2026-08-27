from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from epidemiological_agent.graph.state import (
    AgentState,
)

from epidemiological_agent.graph.nodes import (
    agent_node,
    tools_node,
)

from epidemiological_agent.graph.routing import (
    should_continue,
)

graph_builder = StateGraph(
    AgentState
)

graph_builder.add_node(
    "agent",
    agent_node,
)

graph_builder.add_node(
    "tools",
    tools_node,
)

graph_builder.add_edge(
    START,
    "agent",
)

graph_builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END,
    }, 
)

graph_builder.add_edge(
    "tools",
    "agent"
)

agent_graph = graph_builder.compile()