from langgraph.graph import END

from epidemiological_agent.graph.state import AgentState

def should_continue(
    state: AgentState,
) -> str:
    
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        return "tools"
    
    return END