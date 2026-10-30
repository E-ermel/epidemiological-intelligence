import logging
import time
from datetime import date

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from epidemiological_agent.config import OPENAI_API_KEY
from epidemiological_agent.graph.state import AgentState
from epidemiological_agent.prompts.system_prompt import (
    build_system_prompt,
)
from epidemiological_agent.tools.bigquery_tools import (
    get_max_reference_date,
)

from epidemiological_agent.tools.llm_tools import (
    epidemiological_data_tool,
    total_cases_tool,
    climate_summary_tool,
    outbreak_alerts_tool,
    alert_model_info_tool,
    retrieve_knowledge_tool,
)

tools = [
    epidemiological_data_tool,
    total_cases_tool,
    climate_summary_tool,
    outbreak_alerts_tool,
    alert_model_info_tool,
    retrieve_knowledge_tool,
]

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    api_key=OPENAI_API_KEY or None,
)

llm_with_tools = llm.bind_tools(tools)

logger = logging.getLogger(__name__)

# O gold muda uma vez por mês: uma consulta por hora basta.
_COVERAGE_TTL_SECONDS = 3600
_coverage_cache: dict[str, tuple[float, date | None]] = {}


def _last_data_month() -> date | None:
    """Latest reference_date in the gold table (cached); None on failure."""

    cached = _coverage_cache.get("last")
    if cached is not None and time.time() - cached[0] < _COVERAGE_TTL_SECONDS:
        return cached[1]

    try:
        max_date = get_max_reference_date()
    except Exception:
        logger.exception("Could not read the data coverage for the system prompt")
        return None

    last = max_date.date() if max_date is not None else None
    _coverage_cache["last"] = (time.time(), last)
    return last


def agent_node(
    state: AgentState,
) -> dict:

    messages = state["messages"]

    response = llm_with_tools.invoke(
        [
            {
                "role": "system",
                "content": build_system_prompt(_last_data_month()),
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