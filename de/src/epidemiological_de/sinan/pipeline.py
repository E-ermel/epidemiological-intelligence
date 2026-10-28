"""
SINAN bronze (.dbc por agravo/ano) -> silver de casos.

Grava <SINAN_SILVER_PATH>/part-0.parquet com todos os agravos: são
poucos arquivos (um por agravo e ano), então cabe numa task só.
"""

import fsspec
import pandas as pd

from epidemiological_de import config, dbc, ingestion, storage
from epidemiological_de.sinan import transform
from epidemiological_de.sinan.ingest import FILE_PATTERN


def list_dbc_files(agravo: str, root: str | None = None) -> list[str]:
    root = (root or config.BRONZE_ROOT).rstrip("/")
    fs, base = fsspec.core.url_to_fs(f"{root}/{config.SINAN_SOURCE}/agravo={agravo}")
    protocol = fs.protocol[0] if isinstance(fs.protocol, (list, tuple)) else fs.protocol
    prefix = "" if protocol == "file" else f"{protocol}://"

    return sorted(
        f"{prefix}{path}"
        for path in fs.glob(f"{base}/*")
        if FILE_PATTERN.match(path.rstrip("/").split("/")[-1])
    )


def is_preliminary(path: str) -> bool:
    """O manifesto guarda de que pasta do FTP (FINAIS ou PRELIM) o arquivo veio."""

    manifest = ingestion.read_manifest(path) or {}
    return "/PRELIM/" in manifest.get("url", "")


def file_year(path: str) -> int:
    return 2000 + int(FILE_PATTERN.match(path.rstrip("/").split("/")[-1]).group(2))


def build_silver(root: str | None = None) -> pd.DataFrame:
    per_agravo = []

    for agravo in config.SINAN_AGRAVOS:
        files = list_dbc_files(agravo, root)
        if not files:
            raise FileNotFoundError(
                f"Nenhum .dbc de {agravo} no bronze do SINAN -- rode antes "
                "`python -m epidemiological_de.sinan.ingest`."
            )

        aggregates, preliminary_years = [], set()
        for path in files:
            records = dbc.read_dbc(path, transform.RAW_COLUMNS[agravo])
            events = transform.EVENT_BUILDERS[agravo](records)
            aggregates.append(transform.aggregate_cases(events, config.SINAN_FIRST_YEAR))
            if is_preliminary(path):
                preliminary_years.add(file_year(path))
            print(f"{path.split('/')[-1]}: {len(records)} fichas, {len(events)} casos")

        print(f"{agravo}: anos preliminares {sorted(preliminary_years)}")
        per_agravo.append(transform.mark_provisional(transform.combine(aggregates), preliminary_years))

    return pd.concat(per_agravo, ignore_index=True)


def print_report(silver: pd.DataFrame) -> None:
    summary = silver.groupby(["disease", "year"])["cases"].sum().unstack("year", fill_value=0)
    print(summary.to_string())

    without_occurrence = silver.loc[silver["occurrence_municipality_code"].isna(), "cases"].sum()
    print(f"Casos sem município do evento: {without_occurrence} de {silver['cases'].sum()}")


def run(root: str | None = None, silver_root: str | None = None) -> pd.DataFrame:
    silver = build_silver(root)
    print_report(silver)

    dest_dir = (silver_root or config.SINAN_SILVER_PATH).rstrip("/")
    dest = f"{dest_dir}/part-0.parquet"
    storage.clear_path(dest_dir)
    with fsspec.open(dest, "wb", auto_mkdir=True) as f:
        silver.to_parquet(f, index=False)

    stored = pd.read_parquet(dest)
    if stored["cases"].sum() != silver["cases"].sum():
        raise ValueError("SINAN: total gravado diverge do calculado")

    return silver


if __name__ == "__main__":
    run()
