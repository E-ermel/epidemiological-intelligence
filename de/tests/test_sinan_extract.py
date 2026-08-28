from epidemiological_de import config
from epidemiological_de.sinan import extract


def test_match_disease_maps_known_bronze_filenames():
    assert extract.match_disease("gs://bucket/bronze/sinan/asma.csv") == "ASMA"
    assert (
        extract.match_disease("gs://bucket/bronze/sinan/infarto.csv")
        == "INFARTO AGUDO DO MIOCÁRDIO"
    )


def test_match_disease_is_case_insensitive():
    assert extract.match_disease("gs://bucket/bronze/sinan/ASMA.CSV".lower()) == "ASMA"


def test_match_disease_returns_none_for_unknown_file():
    assert extract.match_disease("gs://bucket/bronze/sinan/unknown.csv") is None


def test_match_disease_covers_every_configured_file():
    for file_name, disease in config.SINAN_DISEASE_MAP.items():
        assert extract.match_disease(f"gs://bucket/bronze/sinan/{file_name}") == disease


def test_read_raw_sinan_csv_keeps_every_column_as_string(tmp_path):
    file_path = tmp_path / "asma.csv"
    file_path.write_bytes(
        "municipio;2023/Jan;2023/Fev\n001 CANOAS;5;SEM\n".encode("ISO-8859-1")
    )

    df = extract.read_raw_sinan_csv(str(file_path))

    assert df.loc[0, "2023/Jan"] == "5"
    assert isinstance(df.loc[0, "2023/Jan"], str)
