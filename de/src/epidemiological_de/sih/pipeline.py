"""
SIH bronze (.dbc por UF/competência) -> silver de internações.

Grava <SIH_SILVER_PATH>/uf=XX/part-0.parquet, uma partição por UF do
hospital (a UF do arquivo). Como MUNIC_MOV é sempre da UF do arquivo,
as partições não se sobrepõem e o gold pode ler a pasta inteira.

Roda com uma task por UF, como a ingestão (CLOUD_RUN_TASK_INDEX /
CLOUD_RUN_TASK_COUNT); localmente, sem essas variáveis, faz todas.
"""

import os

import fsspec
import pandas as pd

from epidemiological_de import config, storage
from epidemiological_de.sih import extract, transform
from epidemiological_de.sih.ingest import task_ufs


def list_dbc_files(uf: str, root: str | None = None) -> list[str]:
    root = (root or config.BRONZE_ROOT).rstrip("/")
    fs, base = fsspec.core.url_to_fs(f"{root}/{config.SIH_SOURCE}/uf={uf}")
    protocol = fs.protocol[0] if isinstance(fs.protocol, (list, tuple)) else fs.protocol
    prefix = "" if protocol == "file" else f"{protocol}://"

    return sorted(
        f"{prefix}{path}"
        for path in fs.glob(f"{base}/*")
        if path.lower().endswith(".dbc")
    )


def process_uf(uf: str, root: str | None = None, silver_root: str | None = None) -> pd.DataFrame:
    files = list_dbc_files(uf, root)
    if not files:
        raise FileNotFoundError(
            f"Nenhum .dbc do SIH para {uf} no bronze -- rode antes "
            "`python -m epidemiological_de.sih.ingest`."
        )

    aggregates, raw_records = [], 0
    for path in files:
        records = extract.read_dbc(path, transform.RAW_COLUMNS)
        raw_records += len(records)
        aggregates.append(transform.aggregate_hospitalizations(records, config.SIH_FIRST_YEAR))

    silver = transform.combine(aggregates)

    dest_dir = f"{(silver_root or config.SIH_SILVER_PATH).rstrip('/')}/uf={uf}"
    dest = f"{dest_dir}/part-0.parquet"
    storage.clear_path(dest_dir)
    with fsspec.open(dest, "wb", auto_mkdir=True) as f:
        silver.to_parquet(f, index=False)

    stored = pd.read_parquet(dest)
    if stored["hospitalizations"].sum() != silver["hospitalizations"].sum():
        raise ValueError(f"{uf}: total gravado diverge do calculado")

    by_disease = silver.groupby("disease")["hospitalizations"].sum().to_dict()
    print(f"{uf}: {len(files)} arquivos, {raw_records} AIHs lidas, {len(silver)} linhas -- {by_disease}")

    return silver


def run(
    root: str | None = None,
    silver_root: str | None = None,
    task_index: int | None = None,
    task_count: int | None = None,
) -> None:
    task_index = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0")) if task_index is None else task_index
    task_count = int(os.getenv("CLOUD_RUN_TASK_COUNT", "1")) if task_count is None else task_count

    for uf in task_ufs(task_index, task_count):
        process_uf(uf, root, silver_root)


if __name__ == "__main__":
    run()
