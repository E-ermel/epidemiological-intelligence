import pandas as pd
import pytest

from epidemiological_de.sih import extract, pipeline, transform


def write_dbf(path, fields, rows, deleted=()):
    """DBF mínimo (dBase III): `fields` = [(nome, largura)], tudo tipo C."""

    record_len = 1 + sum(width for _, width in fields)
    header_len = 32 + 32 * len(fields) + 1

    header = bytearray(32)
    header[0] = 0x03
    header[4:8] = len(rows).to_bytes(4, "little")
    header[8:10] = header_len.to_bytes(2, "little")
    header[10:12] = record_len.to_bytes(2, "little")

    for name, width in fields:
        descriptor = bytearray(32)
        descriptor[0:len(name)] = name.encode("ascii")
        descriptor[11] = ord("C")
        descriptor[16] = width
        header += descriptor
    header += b"\r"

    body = bytearray()
    for i, row in enumerate(rows):
        body += b"*" if i in deleted else b" "
        for (_, width), value in zip(fields, row):
            body += value.encode("latin-1").ljust(width)

    with open(path, "wb") as f:
        f.write(bytes(header) + bytes(body) + b"\x1a")


FIELDS = [("MUNIC_RES", 6), ("MUNIC_MOV", 6), ("DIAG_PRINC", 4), ("DT_INTER", 8), ("IDENT", 1), ("NOME", 10)]


def test_read_dbf_returns_requested_columns_and_skips_deleted(tmp_path):
    path = tmp_path / "x.dbf"
    write_dbf(
        path,
        FIELDS,
        [
            ("431490", "431490", "J450", "20240115", "1", "Conceição"),
            ("430160", "431490", "I219", "20240201", "1", "apagado"),
            ("430160", "430160", "I500", "20231230", "5", ""),
        ],
        deleted={1},
    )

    df = extract.read_dbf(str(path), ["MUNIC_RES", "DIAG_PRINC", "IDENT", "NOME"])

    assert list(df.columns) == ["MUNIC_RES", "DIAG_PRINC", "IDENT", "NOME"]
    assert df.to_dict("records") == [
        {"MUNIC_RES": "431490", "DIAG_PRINC": "J450", "IDENT": "1", "NOME": "Conceição"},
        {"MUNIC_RES": "430160", "DIAG_PRINC": "I500", "IDENT": "5", "NOME": ""},
    ]


def test_read_dbf_fails_on_missing_column(tmp_path):
    path = tmp_path / "x.dbf"
    write_dbf(path, FIELDS, [])

    with pytest.raises(KeyError, match="CID_X"):
        extract.read_dbf(str(path), ["CID_X"])


def test_classify_disease_uses_tabnet_cid_groups():
    diagnosis = pd.Series(["J459", "J210", "J449", "I22", "I509", "A930", "A931", "J47", "I200"])

    assert transform.classify_disease(diagnosis).tolist() == [
        "ASMA",
        "BRONQUITE AGUDA",
        "BRONQUITE CRÔNICA",
        "INFARTO AGUDO DO MIOCÁRDIO",
        "INSUFICIÊNCIA CARDÍACA",
        "OROPOUCHE",
        pd.NA,  # A93.1: outra arbovirose
        pd.NA,  # J47: bronquiectasia, fora dos grupos
        pd.NA,  # I20: angina, não é infarto
    ]


def _records(*rows):
    return pd.DataFrame(rows, columns=transform.RAW_COLUMNS)


def test_aggregate_counts_by_residence_occurrence_and_admission_month():
    records = _records(
        # residente de Canoas internado em Porto Alegre, duas vezes
        ("430460", "431490", "J450", "20240115", "1"),
        ("430460", "431490", "J451", "20240130", "1"),
        # mesma doença e mês, mas internado em Canoas: outra linha
        ("430460", "430460", "J450", "20240110", "1"),
        ("430460", "431490", "J450", "20240115", "5"),  # longa permanência: fora
        ("430460", "431490", "K359", "20240115", "1"),  # apendicite: fora
        ("430460", "431490", "J450", "20141231", "1"),  # antes de first_year: fora
    )

    silver = transform.aggregate_hospitalizations(records, first_year=2015)

    assert list(silver.columns) == transform.SILVER_COLUMNS
    assert sorted(silver.itertuples(index=False, name=None)) == [
        ("ASMA", "430460", "430460", 2024, 1, 1),
        ("ASMA", "430460", "431490", 2024, 1, 2),
    ]


def test_combine_sums_the_same_month_arriving_in_different_competencias():
    january_file = transform.aggregate_hospitalizations(_records(("430460", "431490", "J450", "20240115", "1")), 2015)
    february_file = transform.aggregate_hospitalizations(_records(("430460", "431490", "J450", "20240120", "1")), 2015)

    combined = transform.combine([january_file, february_file])

    assert combined["hospitalizations"].tolist() == [2]


def test_process_uf_writes_partition_per_uf(tmp_path, monkeypatch):
    bronze = tmp_path / "bronze"
    for name in ("RDRS2401.dbc", "RDRS2402.dbc"):
        (bronze / "sih" / "uf=RS").mkdir(parents=True, exist_ok=True)
        (bronze / "sih" / "uf=RS" / name).write_bytes(b"")
        (bronze / "sih" / "uf=RS" / f"{name}.manifest.json").write_text("{}")

    monkeypatch.setattr(
        pipeline.extract,
        "read_dbc",
        lambda path, columns: _records(("430460", "431490", "J450", "20240115", "1")),
    )

    silver_root = str(tmp_path / "silver")
    pipeline.process_uf("RS", root=str(bronze), silver_root=silver_root)

    stored = pd.read_parquet(f"{silver_root}/uf=RS/part-0.parquet")
    assert stored["hospitalizations"].tolist() == [2]  # um por arquivo, manifestos ignorados


def test_process_uf_fails_without_bronze(tmp_path):
    with pytest.raises(FileNotFoundError, match="sih.ingest"):
        pipeline.process_uf("RS", root=str(tmp_path), silver_root=str(tmp_path / "silver"))
