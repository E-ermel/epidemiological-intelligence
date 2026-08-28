import pandas as pd

from epidemiological_de.sinan import transform


def _raw_df():
    return pd.DataFrame(
        {
            "municipio": [
                "431490 PORTO ALEGRE",
                "430510 CANOAS",
                "999999 MUNICIPIO SEM DADO",
            ],
            "2023/Jan": ["5", "SEM", "-"],
            "2023/Fev": ["abc", "3", "0"],
        }
    )


def test_process_sinan_file_maps_month_names_to_numbers():
    df = transform.process_sinan_file(_raw_df(), "ASMA", "asma.csv")

    months = set(df["month"].dropna().unique())
    assert months == {1, 2}


def test_process_sinan_file_parses_cases_per_known_rule():
    df = transform.process_sinan_file(_raw_df(), "ASMA", "asma.csv")

    by_key = df.set_index(["municipality", "month"])["cases"]

    assert by_key[("PORTO ALEGRE", 1)] == 5
    assert pd.isna(by_key[("CANOAS", 1)])
    assert by_key[("MUNICIPIO SEM DADO", 1)] == 0
    assert pd.isna(by_key[("PORTO ALEGRE", 2)])


def test_process_sinan_file_extracts_municipality_code_and_name():
    df = transform.process_sinan_file(_raw_df(), "ASMA", "asma.csv")

    row = df[df["municipality"] == "PORTO ALEGRE"].iloc[0]
    assert row["municipality_code"] == "431490"


def test_process_sinan_file_sets_disease_and_source_columns():
    df = transform.process_sinan_file(_raw_df(), "ASMA", "gs://bucket/asma.csv")

    assert (df["disease"] == "ASMA").all()
    assert (df["source_file"] == "gs://bucket/asma.csv").all()
    assert df["ingestion_timestamp"].notna().all()


def test_process_sinan_file_builds_reference_date_from_year_month():
    df = transform.process_sinan_file(_raw_df(), "ASMA", "asma.csv")

    row = df[(df["municipality"] == "PORTO ALEGRE") & (df["month"] == 1)].iloc[0]
    assert row["reference_date"] == pd.Timestamp("2023-01-01")


def test_process_sinan_file_has_no_duplicate_municipality_month_rows():
    df = transform.process_sinan_file(_raw_df(), "ASMA", "asma.csv")

    duplicate_counts = df.groupby(["municipality_code", "year", "month"]).size()
    assert (duplicate_counts <= 1).all()


def test_process_sinan_file_handles_header_with_no_slash():
    raw = pd.DataFrame({"municipio": ["001 CANOAS"], "TOTAL": ["10"]})

    df = transform.process_sinan_file(raw, "ASMA", "asma.csv")

    assert pd.isna(df.loc[0, "year"])
    assert pd.isna(df.loc[0, "month"])
