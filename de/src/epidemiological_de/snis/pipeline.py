"""Bronze SNIS -> silver de saneamento por município × ano."""

from datetime import date

import fsspec
import pandas as pd

from epidemiological_de import config, ingestion, storage
from epidemiological_de.snis import transform
from epidemiological_de.snis.ingest import FILENAME


def run(
    root: str | None = None,
    silver_path: str | None = None,
    dim_path: str | None = None,
    last_year: int | None = None,
) -> pd.DataFrame:
    path = ingestion.latest_file(config.SNIS_SOURCE, FILENAME, root)
    if path is None:
        raise FileNotFoundError(
            f"{FILENAME} não encontrado no bronze -- rode antes `python -m epidemiological_de.snis.ingest`."
        )

    with fsspec.open(path, "r", encoding="utf-8") as f:
        reported = transform.parse_snis(pd.read_csv(f, dtype={"id_municipio": str}))
    dim = pd.read_parquet(dim_path or config.DIM_MUNICIPALITY_SILVER_PATH)

    sanitation = transform.build_sanitation(
        reported,
        dim,
        config.SNIS_FIRST_YEAR,
        last_year or date.today().year,
        config.SNIS_MAX_CARRY_YEARS,
    )

    print(
        sanitation.groupby("year")
        .agg(
            com_dado=("snis_reference_year", "count"),
            ano_ref_medio=("snis_reference_year", "mean"),
            agua_pct=("snis_water_coverage_pct", "median"),
            esgoto_pct=("snis_sewage_coverage_pct", "median"),
        )
        .round(1)
        .to_string()
    )

    dest_dir = (silver_path or config.SANITATION_SILVER_PATH).rstrip("/")
    storage.clear_path(dest_dir)
    with fsspec.open(f"{dest_dir}/part-0.parquet", "wb", auto_mkdir=True) as f:
        sanitation.to_parquet(f, index=False)

    return sanitation


if __name__ == "__main__":
    run()
