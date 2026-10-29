"""Bronze PRODES -> silver de desmatamento anual por município."""

import json

import fsspec
import pandas as pd

from epidemiological_de import config, ingestion, storage
from epidemiological_de.prodes import ingest, transform


def _read_json(path: str) -> dict:
    with fsspec.open(path, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


def report_unmatched(biomes: list[tuple[pd.DataFrame, set[str], set[int]]], dim: pd.DataFrame) -> None:
    """Código IBGE do INPE fora da dim: área desmatada que se perderia."""

    known = set(dim["municipality_code"])
    lost = pd.concat([df for df, _, _ in biomes])
    lost = lost[~lost["municipality_code"].isin(known)]
    if not lost.empty:
        print(f"Aviso: {lost['deforestation_km2'].sum():.1f} km² em códigos fora da dim:", sorted(lost["municipality_code"].unique()))


def run(root: str | None = None, silver_path: str | None = None, dim_path: str | None = None) -> pd.DataFrame:
    files = ingestion.latest_files(config.PRODES_SOURCE, root)

    biomes = []
    for biome in config.PRODES_BIOMES:
        data_name, loinames_name = ingest.data_file(biome), ingest.loinames_file(biome)
        if data_name not in files or loinames_name not in files:
            raise FileNotFoundError(
                f"{data_name} / {loinames_name} ausentes no bronze -- rode antes "
                "`python -m epidemiological_de.prodes.ingest`."
            )
        parsed = transform.parse_biome(
            _read_json(files[data_name]), _read_json(files[loinames_name]), config.PRODES_FIRST_YEAR
        )
        print(f"{biome}: {len(parsed[1])} municípios, anos {min(parsed[2])}-{max(parsed[2])}")
        biomes.append(parsed)

    dim = pd.read_parquet(dim_path or config.DIM_MUNICIPALITY_SILVER_PATH)
    report_unmatched(biomes, dim)

    deforestation = transform.build_deforestation(biomes, dim)
    print(
        deforestation.groupby("year")
        .agg(km2=("deforestation_km2", "sum"), sem_dado=("deforestation_km2", lambda s: s.isna().sum()))
        .round(0)
        .to_string()
    )

    dest_dir = (silver_path or config.DEFORESTATION_SILVER_PATH).rstrip("/")
    storage.clear_path(dest_dir)
    with fsspec.open(f"{dest_dir}/part-0.parquet", "wb", auto_mkdir=True) as f:
        deforestation.to_parquet(f, index=False)

    return deforestation


if __name__ == "__main__":
    run()
