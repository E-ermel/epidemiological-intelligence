import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dotenv import load_dotenv

from epidemiological_agent.rag.vector_store import (
    build_vector_store,
)

load_dotenv()

vector_store = build_vector_store()

print(
    "Vector store criado com sucesso."
)