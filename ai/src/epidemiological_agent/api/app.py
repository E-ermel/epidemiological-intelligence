from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException

from epidemiological_agent.api.schemas import (
    ChatRequest,
    ChatResponse,
)
from epidemiological_agent.graph.graph import agent_graph

app = FastAPI(
    title="Epidemiological Intelligence API",
     description=(
        "API para interação com o agente "
        "epidemiológico do projeto."
    ),
     version="0.1.0",
)

@app.get("/health")
def health_check():
    return{
        "status": "ok"
    }

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:

    try:
        config = {
            "configurable": {
                "thread_id": request.conversation_id
            }
        }

        result = agent_graph.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": request.message,
                    }
                ]
            },
            config=config,
        )

        answer = result["messages"][-1].content

        return ChatResponse(
            answer=answer,
            conversation_id=request.conversation_id,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a solicitação.",
        ) from exc