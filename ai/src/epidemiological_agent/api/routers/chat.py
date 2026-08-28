import logging

from fastapi import APIRouter, HTTPException

from epidemiological_agent.api.schemas import (
    ChatRequest,
    ChatResponse,
)
from epidemiological_agent.graph.graph import agent_graph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post(
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
