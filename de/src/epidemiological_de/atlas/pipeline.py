"""Bronze Atlas -> silver de indicadores por município × censo."""

import fsspec
import pandas as pd

from epidemiological_de import config, ingestion, storage
from epidemiological_de.atlas import transform
from epidemiological_de.atlas.ingest import FILENAME


def run(root: str | None = None, silver_path: str | None = None) -> pd.DataFrame:
    path = ingestion.latest_file(config.ATLAS_SOURCE, FILENAME, root)
    if path is None:
        raise FileNotFoundError(
            f"{FILENAME} não encontrado no bronze -- rode antes `python -m epidemiological_de.atlas.ingest`."
        )

    with fsspec.open(path, "r", encoding="utf-8") as f:
        atlas = transform.build_atlas(pd.read_csv(f, dtype={"id_municipio": str}))

    print(atlas.groupby("census_year")["idhm"].agg(["count", "mean"]).round(3).to_string())

    dest_dir = (silver_path or config.ATLAS_SILVER_PATH).rstrip("/")
    storage.clear_path(dest_dir)
    with fsspec.open(f"{dest_dir}/part-0.parquet", "wb", auto_mkdir=True) as f:
        atlas.to_parquet(f, index=False)

    return atlas


if __name__ == "__main__":
    run()
