import numpy as np
import pandas as pd

from epidemiological_de.gold import transform


def test_normalize_municipality_collapses_porto_alegre_variants():
    df = pd.DataFrame(
        {
            "municipality": [
                "PORTO ALEGRE - JARDIM BOTANICO",
                "PORTO ALEGRE - BELEM NOVO",
                "CANOAS",
                None,
            ]
        }
    )

    result = transform.normalize_municipality(df)

    normalized = result["municipality_normalized"]
    assert list(normalized[:3]) == ["PORTO ALEGRE", "PORTO ALEGRE", "CANOAS"]
    assert pd.isna(normalized.iloc[3])


def _inmet_fixture():
    return pd.DataFrame(
        {
            "municipality_normalized": [
                "PORTO ALEGRE",
                "PORTO ALEGRE",
                "PORTO ALEGRE",
                "CANOAS",
            ],
            "station_code": ["A801", "A801", "B802", "C803"],
            "timestamp": pd.to_datetime(
                [
                    "2023-01-05",
                    "2023-01-20",
                    "2023-01-10",
                    "2023-01-10",
                ]
            ),
            "precipitation_mm": [10.0, np.nan, 5.0, 2.0],
            "temperature_c": [20.0, 22.0, 21.0, 18.0],
            "dew_point_temperature_c": [10.0, 11.0, 12.0, 9.0],
            "relative_humidity_pct": [80.0, 82.0, 78.0, 70.0],
            "atmospheric_pressure_mb": [1010.0, 1011.0, 1009.0, 1012.0],
            "wind_speed_ms": [1.0, 2.0, 1.5, 0.5],
            "wind_gust_ms": [3.0, 4.0, 3.5, 1.0],
        }
    )


def test_aggregate_station_monthly_sums_and_averages_per_station():
    grouped = transform.aggregate_station_monthly(_inmet_fixture())

    station_a801 = grouped[grouped["station_code"] == "A801"].iloc[0]
    assert station_a801["precipitation_sum_mm"] == 10.0
    assert station_a801["precipitation_avg_observation_mm"] == 10.0
    assert station_a801["temperature_avg_c"] == 21.0


def test_aggregate_station_monthly_keeps_null_precipitation_when_all_missing():
    df = _inmet_fixture()
    df.loc[df["station_code"] == "B802", "precipitation_mm"] = np.nan

    grouped = transform.aggregate_station_monthly(df)

    station_b802 = grouped[grouped["station_code"] == "B802"].iloc[0]
    assert pd.isna(station_b802["precipitation_sum_mm"])


def test_aggregate_municipality_monthly_averages_across_stations_and_counts_them():
    station_monthly = transform.aggregate_station_monthly(_inmet_fixture())

    grouped = transform.aggregate_municipality_monthly(station_monthly)

    porto_alegre = grouped[grouped["municipality"] == "PORTO ALEGRE"].iloc[0]
    assert porto_alegre["station_count"] == 2
    assert porto_alegre["temperature_avg_c"] == 21.0

    canoas = grouped[grouped["municipality"] == "CANOAS"].iloc[0]
    assert canoas["station_count"] == 1


def _sinan_fixture():
    return pd.DataFrame(
        {
            "municipality_code": ["431490", "431490", "430510", "999999"],
            "municipality": ["PORTO ALEGRE", "PORTO ALEGRE", "CANOAS", "SEM CLIMA"],
            "year": [2023, 2023, 2023, 2023],
            "month": [1, 2, 1, 1],
            "reference_date": pd.to_datetime(
                ["2023-01-01", "2023-02-01", "2023-01-01", "2023-01-01"]
            ),
            "cases": [10, 5, 3, 1],
            "disease": ["ASMA", "ASMA", "ASMA", "ASMA"],
        }
    )


def _inmet_monthly_fixture():
    station_monthly = transform.aggregate_station_monthly(_inmet_fixture())
    return transform.aggregate_municipality_monthly(station_monthly)


def test_join_gold_preserves_sinan_row_count():
    sinan_df = _sinan_fixture()
    gold_df = transform.join_gold(sinan_df, _inmet_monthly_fixture())

    assert len(gold_df) == len(sinan_df)


def test_join_gold_keeps_epidemiological_record_without_climate_match():
    sinan_df = _sinan_fixture()
    gold_df = transform.join_gold(sinan_df, _inmet_monthly_fixture())

    missing_climate_row = gold_df[gold_df["municipality"] == "SEM CLIMA"]
    assert len(missing_climate_row) == 1
    assert pd.isna(missing_climate_row.iloc[0]["precipitation_sum_mm"])
    assert missing_climate_row.iloc[0]["cases"] == 1


def test_join_gold_attaches_matching_climate_values():
    sinan_df = _sinan_fixture()
    gold_df = transform.join_gold(sinan_df, _inmet_monthly_fixture())

    jan_porto_alegre = gold_df[
        (gold_df["municipality"] == "PORTO ALEGRE") & (gold_df["month"] == 1)
    ].iloc[0]
    assert jan_porto_alegre["temperature_avg_c"] == 21.0


def _raw_inmet_fixture():
    return _inmet_fixture().rename(columns={"municipality_normalized": "municipality"})


def test_build_gold_has_no_duplicate_disease_municipality_year_month_keys():
    gold_df = transform.build_gold(_raw_inmet_fixture(), _sinan_fixture())

    duplicate_counts = gold_df.groupby(
        ["disease", "municipality", "year", "month"]
    ).size()
    assert (duplicate_counts <= 1).all()


def test_build_gold_preserves_sinan_cardinality_end_to_end():
    sinan_df = _sinan_fixture()

    gold_df = transform.build_gold(_raw_inmet_fixture(), sinan_df)

    assert len(gold_df) == len(sinan_df)
