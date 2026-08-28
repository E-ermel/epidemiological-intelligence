from pydantic import BaseModel, Field
class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Mensagem enviada ao agente.",
    )

    conversation_id: str = Field(
        ...,
        min_length=1,
        description="Identificador da conversa.",
    )

class ChatResponse(BaseModel):
    answer: str
    conversation_id: str