from dotenv import load_dotenv
import logging
import os

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from epidemiological_agent.api.schemas import (
    ChatRequest,
    ChatResponse,
)
from epidemiological_agent.logging_config import (
    configure_logging,
)
from epidemiological_agent.graph.graph import agent_graph
configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Epidemiological Intelligence API",
     description=(
        "API para interação com o agente "
        "epidemiológico do projeto."
    ),
     version="0.1.0",
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

@app.get("/")
def root():
    return {
        "service": "Epidemiological Intelligence API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }

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

    logger.info(
        "Processing chat request | conversation_id=%s",
        request.conversation_id,
    )

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

        logger.info(
            "Chat request completed | conversation_id=%s",
            request.conversation_id,
        )

        return ChatResponse(
            answer=answer,
            conversation_id=request.conversation_id,
        )

    except Exception:
        logger.exception(
            "Chat request failed | conversation_id=%s",
            request.conversation_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a solicitação.",
        )