import os
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))

os.environ.setdefault("GCP_PROJECT_ID", "test-project")
