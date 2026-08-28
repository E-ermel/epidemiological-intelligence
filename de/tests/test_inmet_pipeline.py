from epidemiological_de.inmet import pipeline


HEADER = (
    "REGIAO:;S\n"
    "UF:;RS\n"
    "ESTACAO:;PORTO ALEGRE - JARDIM BOTANICO\n"
    "CODIGO (WMO):;A801\n"
    "LATITUDE:;-30,05\n"
    "LONGITUDE:;-51,17\n"
    "ALTITUDE:;41,18\n"
    "DATA DE FUNDACAO:;01/01/2000\n"
)

DATA_ROW = "2023-01-01;0000 UTC;0,0;1013,2;X;X;X;25,4;18,2;X;X;X;X;X;X;80;120;5,2;3,1;\n"


def _write_bronze_file(path, header=HEADER, rows=(DATA_ROW,)):
    path.write_bytes((header + "".join(rows)).encode("ISO-8859-1"))


def test_parse_inmet_file_reads_bronze_csv_end_to_end(tmp_path):
    file_path = tmp_path / "INMET_S_RS_A801_PORTO ALEGRE_01-01-2023.CSV"
    _write_bronze_file(file_path)

    df = pipeline.parse_inmet_file(str(file_path))

    assert len(df) == 1
    assert df.loc[0, "municipality"] == "PORTO ALEGRE - JARDIM BOTANICO"
    assert df.loc[0, "temperature_c"] == 25.4


def test_build_inmet_silver_preserves_total_record_count_across_files(tmp_path):
    file_a = tmp_path / "station_a.csv"
    file_b = tmp_path / "station_b.csv"
    _write_bronze_file(file_a, rows=(DATA_ROW, DATA_ROW))
    _write_bronze_file(file_b, rows=(DATA_ROW,))

    df = pipeline.build_inmet_silver([str(file_a), str(file_b)])

    assert len(df) == 3
    assert "year" in df.columns


def test_build_inmet_silver_raises_when_no_files_given():
    try:
        pipeline.build_inmet_silver([])
    except ValueError:
        return

    raise AssertionError("expected ValueError for empty file list")
