import pandas as pd

from epidemiological_de.inmet import transform


def _data_line(
    date="2023-01-01",
    hour="0000 UTC",
    precipitation="0,0",
    pressure="1013,2",
    temperature="25,4",
    dew_point="18,2",
    humidity="80",
    wind_direction="120",
    wind_gust="5,2",
    wind_speed="3,1",
):
    fields = [None] * 19
    fields[0] = date
    fields[1] = hour
    fields[2] = precipitation
    fields[3] = pressure
    fields[7] = temperature
    fields[8] = dew_point
    fields[15] = humidity
    fields[16] = wind_direction
    fields[17] = wind_gust
    fields[18] = wind_speed
    return ";".join("" if f is None else f for f in fields)


METADATA = {
    "station_name": "PORTO ALEGRE - JARDIM BOTANICO",
    "station_code": "A801",
    "state": "RS",
    "latitude": "-30.05",
    "longitude": "-51.17",
    "altitude": "41.18",
}


def test_build_silver_dataframe_accepts_dash_date_format():
    lines = [_data_line(date="2023-01-15", hour="1200")]

    df = transform.build_silver_dataframe(lines, METADATA, "file.csv")

    assert df.loc[0, "timestamp"] == pd.Timestamp("2023-01-15 12:00")


def test_build_silver_dataframe_accepts_slash_date_format():
    lines = [_data_line(date="2023/01/15", hour="1200")]

    df = transform.build_silver_dataframe(lines, METADATA, "file.csv")

    assert df.loc[0, "timestamp"] == pd.Timestamp("2023-01-15 12:00")


def test_build_silver_dataframe_parses_utc_suffixed_hour():
    lines = [_data_line(hour="0300 UTC")]

    df = transform.build_silver_dataframe(lines, METADATA, "file.csv")

    assert df.loc[0, "timestamp"] == pd.Timestamp("2023-01-01 03:00")


def test_build_silver_dataframe_converts_comma_decimals():
    lines = [_data_line(temperature="25,4", precipitation="1,5")]

    df = transform.build_silver_dataframe(lines, METADATA, "file.csv")

    assert df.loc[0, "temperature_c"] == 25.4
    assert df.loc[0, "precipitation_mm"] == 1.5


def test_build_silver_dataframe_treats_sentinel_and_blank_as_null():
    lines = [
        _data_line(precipitation="-9999"),
        _data_line(precipitation=""),
    ]

    df = transform.build_silver_dataframe(lines, METADATA, "file.csv")

    assert df["precipitation_mm"].isna().all()


def test_build_silver_dataframe_attaches_station_metadata():
    lines = [_data_line()]

    df = transform.build_silver_dataframe(lines, METADATA, "gs://bucket/file.csv")

    assert df.loc[0, "station_code"] == "A801"
    assert df.loc[0, "municipality"] == "PORTO ALEGRE - JARDIM BOTANICO"
    assert df.loc[0, "latitude"] == -30.05
    assert df.loc[0, "source_file"] == "gs://bucket/file.csv"


def test_standardize_inmet_silver_falls_back_to_filename_municipality():
    metadata_without_station = {k: v for k, v in METADATA.items() if k != "station_name"}
    lines = [_data_line()]
    file_path = "gs://bucket/bronze/INMET_S_RS_A801_CAXIAS DO SUL_01-01-2023.CSV"

    df = transform.build_silver_dataframe(lines, metadata_without_station, file_path)
    df = transform.standardize_inmet_silver(df)

    assert df.loc[0, "municipality"] == "CAXIAS DO SUL"
    assert df.loc[0, "station_name"] == "CAXIAS DO SUL"


def test_standardize_inmet_silver_keeps_header_municipality_when_present():
    lines = [_data_line()]

    df = transform.build_silver_dataframe(lines, METADATA, "file.csv")
    df = transform.standardize_inmet_silver(df)

    assert df.loc[0, "municipality"] == "PORTO ALEGRE - JARDIM BOTANICO"


def test_standardize_inmet_silver_derives_year_from_timestamp():
    lines = [_data_line(date="2022-12-31", hour="2300")]

    df = transform.build_silver_dataframe(lines, METADATA, "file.csv")
    df = transform.standardize_inmet_silver(df)

    assert df.loc[0, "year"] == 2022
