"""
Leitura dos .dbc do DATASUS (SIH, SINAN...).

O .dbc é um .dbf comprimido (formato próprio do DATASUS). O pyreaddbc
descomprime para .dbf, e o .dbf é lido aqui direto com numpy: são
registros de largura fixa, então cada coluna é uma fatia de bytes. O
dbfread (puro Python, registro a registro) levava ~7 s por arquivo do
RS; assim leva ~0,15 s -- diferença que importa nos ~3.800 arquivos do
Brasil.
"""

import os
import tempfile

import fsspec
import numpy as np
import pandas as pd
import pyreaddbc

DBF_HEADER_END = 0x0D
DBF_DELETED_FLAG = ord("*")


def read_dbf(path: str, columns: list[str], encoding: str = "latin-1") -> pd.DataFrame:
    """
    Colunas pedidas de um .dbf local, todas como texto sem espaços nas
    pontas (o DBF guarda números como texto também). Registros marcados
    como apagados ficam de fora.
    """

    with open(path, "rb") as f:
        raw = f.read()

    n_records = int.from_bytes(raw[4:8], "little")
    header_len = int.from_bytes(raw[8:10], "little")
    record_len = int.from_bytes(raw[10:12], "little")

    # Descritores de campo: 32 bytes cada, a partir do byte 32, até o
    # terminador. O byte 0 de cada registro é a flag de apagado.
    fields: dict[str, tuple[int, int]] = {}
    offset, pos = 1, 32
    while raw[pos] != DBF_HEADER_END:
        name = raw[pos:pos + 11].split(b"\0")[0].decode("ascii").upper()
        length = raw[pos + 16]
        fields[name] = (offset, length)
        offset += length
        pos += 32

    missing = [column for column in columns if column not in fields]
    if missing:
        raise KeyError(f"Colunas ausentes em {path}: {missing}")

    records = np.frombuffer(raw, dtype=np.uint8, count=n_records * record_len, offset=header_len)
    records = records.reshape(n_records, record_len)
    records = records[records[:, 0] != DBF_DELETED_FLAG]

    data = {}
    for column in columns:
        start, length = fields[column]
        values = np.ascontiguousarray(records[:, start:start + length]).view(f"S{length}").ravel()
        data[column] = pd.Series(values, dtype=object).str.decode(encoding).str.strip()

    return pd.DataFrame(data)


def read_dbc(path: str, columns: list[str]) -> pd.DataFrame:
    """Lê um .dbc (local ou no GCS) via arquivos temporários locais."""

    with tempfile.TemporaryDirectory() as tmp:
        local_dbc = os.path.join(tmp, "file.dbc")
        local_dbf = os.path.join(tmp, "file.dbf")

        with fsspec.open(path, "rb") as src, open(local_dbc, "wb") as dst:
            dst.write(src.read())

        pyreaddbc.dbc2dbf(local_dbc, local_dbf)
        return read_dbf(local_dbf, columns)
