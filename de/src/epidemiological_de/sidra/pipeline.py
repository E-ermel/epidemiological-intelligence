"""
Bronze SIDRA -> silver de população e densidade por município × ano.

Lê a versão mais recente de cada arquivo ingerido por sidra/ingest.py
e a área de cada município da dim_municipality.
"""

import json
import re

import fsspec
import pandas as pd

from epidemiological_de import config, ingestion, storage
from epidemiological_de.sidra import transform
from epidemiological_de.sidra.ingest import CENSUS_FILE

ESTIMATE_PATTERN = re.compile(r"^populacao_estimada_\d{4}\.json$")


def _read_json(path: str) -> list[dict]:
    with fsspec.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_quality(population: pd.DataFrame, dim: pd.DataFrame) -> None:
    per_year = population.groupby("year").agg(
        municipios=("municipality_code", "nunique"),
        populacao=("population", "sum"),
    )
    print(per_year.to_string())
    print(population.groupby("population_source").size().to_dict())

    # Ano com bem menos municípios que a dim: resposta truncada da API.
    incomplete = per_year[per_year["municipios"] < len(dim) * 0.99]
    if not incomplete.empty:
        raise ValueError(f"Anos com população faltando para muitos municípios: {incomplete.index.tolist()}")


def run(root: str | None = None, silver_path: str | None = None, dim_path: str | None = None) -> pd.DataFrame:
    files = ingestion.latest_files(config.SIDRA_SOURCE, root)

    estimate_paths = [path for name, path in sorted(files.items()) if ESTIMATE_PATTERN.match(name)]
    if not estimate_paths or CENSUS_FILE not in files:
        raise FileNotFoundError(
            "Estimativas ou Censo 2022 ausentes no bronze do SIDRA -- rode antes "
            "`python -m epidemiological_de.sidra.ingest`."
        )

    estimates = pd.concat(
        [transform.parse_sidra(_read_json(path), transform.ESTIMATE) for path in estimate_paths],
        ignore_index=True,
    )
    census = transform.parse_sidra(_read_json(files[CENSUS_FILE]), transform.CENSUS)
    dim = pd.read_parquet(dim_path or config.DIM_MUNICIPALITY_SILVER_PATH)

    population = transform.build_population(estimates, census, dim)
    check_quality(population, dim)

    dest_dir = (silver_path or config.POPULATION_SILVER_PATH).rstrip("/")
    storage.clear_path(dest_dir)
    with fsspec.open(f"{dest_dir}/part-0.parquet", "wb", auto_mkdir=True) as f:
        population.to_parquet(f, index=False)

    return population


if __name__ == "__main__":
    run()
