from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from epidemiological_agent.config import OPENAI_API_KEY
from epidemiological_agent.graph.state import AgentState
from epidemiological_agent.prompts.system_prompt import (
    SYSTEM_PROMPT,
)

from epidemiological_agent.tools.llm_tools import (
    epidemiological_data_tool,
    total_cases_tool,
    climate_summary_tool,
    model_metrics_tool,
    model_predictions_tool,
    municipality_model_metrics_tool,
    retrieve_knowledge_tool,
)

tools = [
    epidemiological_data_tool,
    total_cases_tool,
    climate_summary_tool,
    model_metrics_tool,
    model_predictions_tool,
    municipality_model_metrics_tool,
    retrieve_knowledge_tool,
]

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    api_key=OPENAI_API_KEY or None,
)

llm_with_tools = llm.bind_tools(tools)

def agent_node(
    state: AgentState,
) -> dict:
    
    messages = state["messages"]
    
    response = llm_with_tools.invoke(
        [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            *messages,
        ]
    )
    return{
        "messages": [response]
    }

tools_node = ToolNode(
    tools=tools
)