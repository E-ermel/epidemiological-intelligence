import re
from itertools import islice
from typing import Dict, List

import fsspec


DATA_LINE_PATTERN = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2};")


def list_csv_files(path: str) -> List[str]:
    fs, root = fsspec.core.url_to_fs(path)
    protocol = fs.protocol[0] if isinstance(fs.protocol, (list, tuple)) else fs.protocol

    all_paths = fs.find(root)
    return sorted(
        f"{protocol}://{file_path}"
        for file_path in all_paths
        if file_path.lower().endswith(".csv")
    )


def read_raw_lines(file_path: str) -> List[str]:
    with fsspec.open(file_path, "rb") as f:
        content = f.read()

    text = content.decode("ISO-8859-1")
    return re.split(r"\r?\n", text)


def extract_metadata(lines: List[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}

    # islice para nao varrer o arquivo inteiro: o cabecalho esta nas
    # primeiras linhas, como no .limit(8) do notebook original.
    header_lines = islice(
        (line for line in lines if not DATA_LINE_PATTERN.match(line)),
        8,
    )

    for line in header_lines:
        if ";" not in line:
            continue

        key, value = line.split(";", 1)
        key = key.strip().upper()
        value = value.strip()

        if "ESTAÇÃO" in key or "ESTACAO" in key:
            metadata["station_name"] = value
        elif "CODIGO" in key:
            metadata["station_code"] = value
        elif key.startswith("UF"):
            metadata["state"] = value
        elif "LATITUDE" in key:
            metadata["latitude"] = value.replace(",", ".")
        elif "LONGITUDE" in key:
            metadata["longitude"] = value.replace(",", ".")
        elif "ALTITUDE" in key:
            metadata["altitude"] = value.replace(",", ".")

    return metadata
