"""
Roda o benchmark inteiro, cada modelo num processo próprio.

Uso: python run_all.py <pasta do gold>

Pré-requisito: o ambiente do benchmark (Python 3.11, ver README.md).
"""

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent

STEPS = [
    ["prepare.py", "{gold}"],
    ["run_seasonal_naive.py"],
    ["run_glm.py"],
    ["run_chronos.py"],
    ["run_timesfm.py"],
    ["run_moirai.py"],
    ["run_neuralforecast.py", "patchtst", "nacional"],
    ["run_neuralforecast.py", "patchtst", "estado"],
    ["run_neuralforecast.py", "tft", "nacional"],
    ["run_neuralforecast.py", "tft", "estado"],
    ["evaluate.py"],
]


def main(gold: str) -> None:
    for step in STEPS:
        command = [sys.executable, str(HERE / step[0]), *(arg.format(gold=gold) for arg in step[1:])]
        started = time.time()
        print(f"\n=== {' '.join(step)}", flush=True)
        subprocess.run(command, check=True, cwd=HERE)
        print(f"=== {step[0]}: {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
