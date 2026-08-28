from dotenv import load_dotenv
import os

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from epidemiological_agent.logging_config import (
    configure_logging,
)
from epidemiological_agent.api.routers import chat
configure_logging()

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

app.include_router(chat.router)


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