"""Bronze MapBiomas -> silver de uso do solo (%) por município × ano."""

import fsspec
import pandas as pd

from epidemiological_de import config, ingestion, storage
from epidemiological_de.mapbiomas import transform
from epidemiological_de.mapbiomas.ingest import FILENAME


def run(root: str | None = None, silver_path: str | None = None) -> pd.DataFrame:
    path = ingestion.latest_file(config.MAPBIOMAS_SOURCE, FILENAME, root)
    if path is None:
        raise FileNotFoundError(
            f"{FILENAME} não encontrado no bronze -- rode antes `python -m epidemiological_de.mapbiomas.ingest`."
        )

    with fsspec.open(path, "r", encoding="utf-8") as f:
        land_cover = transform.build_land_cover(pd.read_csv(f, dtype={"id_municipio": str}))

    print(land_cover.groupby("year")[transform.GOLD_FEATURES].mean().round(1).to_string())

    dest_dir = (silver_path or config.LAND_COVER_SILVER_PATH).rstrip("/")
    storage.clear_path(dest_dir)
    with fsspec.open(f"{dest_dir}/part-0.parquet", "wb", auto_mkdir=True) as f:
        land_cover.to_parquet(f, index=False)

    return land_cover


if __name__ == "__main__":
    run()
