"""
Ingestão SIH/SUS -> bronze (fonte 🟢 oficial).

Baixa a AIH reduzida (RD{UF}{AA}{MM}.dbc, uma por UF e competência de
processamento) do FTP do DATASUS para bronze/sih/uf=XX/, com manifesto.
O .dbc é guardado como veio; a leitura e o filtro por CID ficam no
silver.

Um LIST da pasta traz tamanho e data de todos os arquivos de uma vez;
só baixa o que é novo ou mudou desde a última ingestão. O DATASUS
republica competências antigas (AIHs aprovadas com atraso), então não
basta baixar cada arquivo uma vez só.

Roda como Cloud Run Job com uma task por UF (CLOUD_RUN_TASK_INDEX /
CLOUD_RUN_TASK_COUNT); localmente, sem essas variáveis, faz todas as
UFs. Precisa rodar em southamerica-east1, como as outras ingestões de
fontes do governo (ver var.ingest_region no Terraform).
"""

import os
import re
import sys

from epidemiological_de import config, ingestion

FILE_PATTERN = re.compile(r"^RD([A-Z]{2})(\d{2})(\d{2})\.DBC$", re.IGNORECASE)


def task_ufs(index: int, count: int) -> list[str]:
    """UFs desta task: a i-ésima de cada `count`, para dividir o país."""

    return config.UFS[index::count]


def files_to_ingest(listing: dict[str, dict], ufs: list[str], first_year: int) -> list[str]:
    """Arquivos RD das `ufs`, de `first_year` em diante, em ordem."""

    selected = []

    for name in listing:
        match = FILE_PATTERN.match(name)
        if match is None:
            continue

        uf, yy, _ = match.groups()
        if uf.upper() in ufs and 2000 + int(yy) >= first_year:
            selected.append(name)

    return sorted(selected)


def dbc_path(name: str, root: str | None = None) -> str:
    root = (root or config.BRONZE_ROOT).rstrip("/")
    uf = FILE_PATTERN.match(name).group(1).upper()
    return f"{root}/{config.SIH_SOURCE}/uf={uf}/{name}"


def run(
    client: ingestion.FtpClient | None = None,
    root: str | None = None,
    task_index: int | None = None,
    task_count: int | None = None,
) -> dict[str, str | None]:
    client = client or ingestion.FtpClient(config.DATASUS_FTP_HOST)
    task_index = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0")) if task_index is None else task_index
    task_count = int(os.getenv("CLOUD_RUN_TASK_COUNT", "1")) if task_count is None else task_count

    ufs = task_ufs(task_index, task_count)
    listing = client.list_dir(config.SIH_FTP_DIR)
    names = files_to_ingest(listing, ufs, config.SIH_FIRST_YEAR)

    print(f"Task {task_index + 1}/{task_count}: UFs {', '.join(ufs)} -- {len(names)} arquivos")

    if not names:
        raise RuntimeError(
            f"Nenhum arquivo RD para {ufs} em {config.SIH_FTP_DIR}: "
            "a pasta mudou de nome ou o LIST veio vazio?"
        )

    written: dict[str, str | None] = {}
    failed: dict[str, Exception] = {}

    for name in names:
        # Uma falha não interrompe as outras competências: o próximo
        # run tenta de novo só o que faltou.
        try:
            written[name] = ingestion.ftp_download_if_changed(
                client,
                f"{config.SIH_FTP_DIR}/{name}",
                listing[name],
                dbc_path(name, root),
                source=config.SIH_SOURCE,
                source_type="oficial",
            )
        except Exception as error:
            failed[name] = error
            print(f"{name}: ERRO {error}", file=sys.stderr)
            continue

        if written[name] is not None:
            print(f"{name}: baixado")

    unchanged = sum(path is None for path in written.values())
    print(f"{len(written) - unchanged} baixados, {unchanged} sem mudança, {len(failed)} com erro")

    if failed:
        raise RuntimeError(f"{len(failed)} arquivo(s) falharam: {', '.join(sorted(failed))}")

    return written


if __name__ == "__main__":
    run()
