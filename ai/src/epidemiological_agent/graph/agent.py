from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from epidemiological_agent.prompts.system_prompt import (
    SYSTEM_PROMPT,
)

from langchain.agents import create_agent

load_dotenv()

from epidemiological_agent.tools.llm_tools import (
    epidemiological_data_tool,
    total_cases_tool,
    model_metrics_tool,
    model_predictions_tool,
    municipality_model_metrics_tool,
)

tools = [
    epidemiological_data_tool,
    total_cases_tool,
    model_metrics_tool,
    model_predictions_tool,
    municipality_model_metrics_tool,
]

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)