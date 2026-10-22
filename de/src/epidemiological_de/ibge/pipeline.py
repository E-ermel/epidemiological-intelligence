"""
Bronze IBGE -> silver dim_municipality (+ BigQuery).

Lê a versão mais recente de cada arquivo ingerido por ibge/ingest.py.
"""

import json

import fsspec
import pandas as pd

from epidemiological_de import config, ingestion, storage, warehouse
from epidemiological_de.ibge.ingest import MALHA_METADADOS_FILE, MUNICIPIOS_FILE
from epidemiological_de.ibge.transform import build_dim_municipality


def _read_latest_json(filename: str, root: str | None = None) -> list[dict]:
    path = ingestion.latest_file(config.IBGE_SOURCE, filename, root)
    if path is None:
        raise FileNotFoundError(
            f"{filename} não encontrado no bronze do IBGE -- rode antes "
            f"`python -m epidemiological_de.ibge.ingest`."
        )

    print("Lendo:", path)
    with fsspec.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_quality(dim: pd.DataFrame) -> None:
    print("Municípios:", len(dim))
    print("UFs:", dim["state"].nunique())
    print("Sem lat/lon/área:", dim["latitude"].isna().sum())

    duplicated_codes = dim["municipality_code"].duplicated().sum()
    if duplicated_codes:
        raise ValueError(f"{duplicated_codes} códigos de município duplicados.")

    if dim["state"].nunique() != 27:
        raise ValueError(f"Esperadas 27 UFs, encontradas {dim['state'].nunique()}.")

    # Brasil tem ~5.570 municípios; uma queda grande indica resposta
    # truncada ou mudança de formato da API, não criação/extinção real.
    if len(dim) < 5500:
        raise ValueError(f"Apenas {len(dim)} municípios -- resposta do IBGE incompleta?")

    # Chave alternativa usada pelo DATASUS: também precisa ser única.
    if dim["municipality_code_6"].duplicated().any():
        raise ValueError("Código de 6 dígitos duplicado -- não serve como chave DATASUS.")


def run(root: str | None = None) -> pd.DataFrame:
    dim = build_dim_municipality(
        _read_latest_json(MUNICIPIOS_FILE, root),
        _read_latest_json(MALHA_METADADOS_FILE, root),
    )

    check_quality(dim)

    storage.clear_path(config.DIM_MUNICIPALITY_SILVER_PATH)
    dim.to_parquet(f"{config.DIM_MUNICIPALITY_SILVER_PATH}part-0.parquet", index=False)

    stored = len(pd.read_parquet(config.DIM_MUNICIPALITY_SILVER_PATH))
    if stored != len(dim):
        raise ValueError(f"Silver row count mismatch: original={len(dim)}, stored={stored}")

    loaded_rows = warehouse.load_dataframe(dim, config.DIM_MUNICIPALITY_TABLE_ID)
    print("BigQuery:", loaded_rows, "linhas em", config.DIM_MUNICIPALITY_TABLE_ID)

    return dim


if __name__ == "__main__":
    run()
