from typing import List, Optional

import gcsfs
import pandas as pd

from epidemiological_de import config


def list_bronze_files() -> List[str]:
    fs = gcsfs.GCSFileSystem()
    entries = fs.ls(config.SINAN_BRONZE_PATH, detail=False)
    return [entry if entry.startswith("gs://") else f"gs://{entry}" for entry in entries]


def match_disease(file_path: str) -> Optional[str]:
    file_name = file_path.rstrip("/").split("/")[-1].strip().lower()
    return config.SINAN_DISEASE_MAP.get(file_name)


def read_raw_sinan_csv(file_path: str) -> pd.DataFrame:
    # dtype=str mirrors Spark reading every column as string: sem inferência de
    # tipo, valores como "5" não viram 5.0 e escapam do parsing de cases.
    return pd.read_csv(file_path, sep=";", encoding="ISO-8859-1", dtype=str)
