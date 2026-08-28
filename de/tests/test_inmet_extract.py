from epidemiological_de.inmet import extract


HEADER_LINES = [
    "REGIAO:;S",
    "UF:;RS",
    "ESTACAO:;PORTO ALEGRE - JARDIM BOTANICO",
    "CODIGO (WMO):;A801",
    "LATITUDE:;-30,05",
    "LONGITUDE:;-51,17",
    "ALTITUDE:;41,18",
    "DATA DE FUNDACAO:;01/01/2000",
]

DATA_LINE = (
    "2023-01-01;0000 UTC;0,0;1013,2;X;X;X;25,4;18,2;"
    "X;X;X;X;X;X;80;120;5,2;3,1;"
)


def test_extract_metadata_reads_known_fields():
    metadata = extract.extract_metadata(HEADER_LINES + [DATA_LINE])

    assert metadata["station_name"] == "PORTO ALEGRE - JARDIM BOTANICO"
    assert metadata["station_code"] == "A801"
    assert metadata["state"] == "RS"
    assert metadata["latitude"] == "-30.05"
    assert metadata["longitude"] == "-51.17"
    assert metadata["altitude"] == "41.18"


def test_extract_metadata_only_scans_first_eight_non_data_lines():
    extra_header = HEADER_LINES + ["LATITUDE ALTERNATIVA:;-99,99"]

    metadata = extract.extract_metadata(extra_header + [DATA_LINE])

    assert metadata["latitude"] == "-30.05"


def test_extract_metadata_ignores_lines_without_separator():
    lines = ["no separator here"] + HEADER_LINES

    metadata = extract.extract_metadata(lines)

    assert metadata["station_code"] == "A801"


def test_read_raw_lines_decodes_iso8859_1(tmp_path):
    file_path = tmp_path / "estacao.csv"
    file_path.write_bytes("ESTACAO:;SÃO LEOPOLDO\n".encode("ISO-8859-1"))

    lines = extract.read_raw_lines(str(file_path))

    assert lines[0] == "ESTACAO:;SÃO LEOPOLDO"


def test_list_csv_files_filters_by_extension_and_sorts(tmp_path):
    (tmp_path / "b.csv").write_text("b")
    (tmp_path / "a.csv").write_text("a")
    (tmp_path / "readme.txt").write_text("ignored")

    files = extract.list_csv_files(str(tmp_path))

    assert len(files) == 2
    assert files[0].endswith("a.csv")
    assert files[1].endswith("b.csv")
