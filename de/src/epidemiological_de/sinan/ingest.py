"""
Ingestão SINAN -> bronze (fonte 🟢 oficial).

Baixa do FTP do DATASUS um arquivo nacional por agravo e ano
({AGRAVO}BR{AA}.dbc) para bronze/sinan/agravo=XXXX/, com manifesto.

Cada ano está em FINAIS (base fechada) ou PRELIM (ainda recebendo
fichas). Quando existe nas duas pastas, vale FINAIS. A passagem de
PRELIM para FINAIS muda o arquivo remoto, então ele é baixado de novo
para o mesmo caminho no bronze.

Arquivos pequenos (~200 MB no total): uma task só. Roda em
southamerica-east1, como as outras ingestões de fontes do governo.
"""

import re
import sys

from epidemiological_de import config, ingestion

FILE_PATTERN = re.compile(r"^([A-Z]{4})BR(\d{2})\.DBC$", re.IGNORECASE)


def select_files(
    listings: dict[str, dict[str, dict]],
    agravos: list[str],
    first_year: int,
) -> dict[str, tuple[str, str, dict]]:
    """
    {ARQUIVO: (pasta, nome no FTP, entrada do LIST)} dos `agravos` desde
    `first_year`, preferindo FINAIS a PRELIM quando o ano está nas duas.
    A chave é o nome em maiúsculas: o FTP não é consistente na caixa.
    """

    selected: dict[str, tuple[str, str, dict]] = {}

    # PRELIM primeiro, FINAIS por cima.
    for folder in ("PRELIM", "FINAIS"):
        for name, entry in listings.get(folder, {}).items():
            match = FILE_PATTERN.match(name)
            if match is None:
                continue

            agravo, yy = match.groups()
            if agravo.upper() in agravos and 2000 + int(yy) >= first_year:
                selected[name.upper()] = (folder, name, entry)

    return {key: selected[key] for key in sorted(selected)}


def dbc_path(name: str, root: str | None = None) -> str:
    root = (root or config.BRONZE_ROOT).rstrip("/")
    agravo = FILE_PATTERN.match(name).group(1).upper()
    return f"{root}/{config.SINAN_SOURCE}/agravo={agravo}/{name.upper()}"


def run(client: ingestion.FtpClient | None = None, root: str | None = None) -> dict[str, str | None]:
    client = client or ingestion.FtpClient(config.DATASUS_FTP_HOST)

    listings = {folder: client.list_dir(path) for folder, path in config.SINAN_FTP_DIRS.items()}
    files = select_files(listings, config.SINAN_AGRAVOS, config.SINAN_FIRST_YEAR)

    missing = [agravo for agravo in config.SINAN_AGRAVOS if not any(key.startswith(agravo) for key in files)]
    if missing:
        raise RuntimeError(
            f"Nenhum arquivo de {missing} no FTP do SINAN: a pasta mudou ou o LIST veio vazio?"
        )

    written: dict[str, str | None] = {}
    failed: dict[str, Exception] = {}

    for key, (folder, name, entry) in files.items():
        try:
            written[key] = ingestion.ftp_download_if_changed(
                client,
                f"{config.SINAN_FTP_DIRS[folder]}/{name}",
                entry,
                dbc_path(name, root),
                source=config.SINAN_SOURCE,
                source_type="oficial",
            )
        except Exception as error:
            failed[key] = error
            print(f"{key}: ERRO {error}", file=sys.stderr)
            continue

        if written[key] is not None:
            print(f"{key} ({folder}): baixado")

    unchanged = sum(path is None for path in written.values())
    print(f"{len(written) - unchanged} baixados, {unchanged} sem mudança, {len(failed)} com erro")

    if failed:
        raise RuntimeError(f"{len(failed)} arquivo(s) falharam: {', '.join(sorted(failed))}")

    return written


if __name__ == "__main__":
    run()
