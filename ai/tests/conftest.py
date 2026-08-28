import os
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))

# graph.nodes builds a ChatOpenAI client at import time; tests never call the
# real API (the LLM call is monkeypatched), but the client still validates
# that a key-shaped value is present at construction.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
