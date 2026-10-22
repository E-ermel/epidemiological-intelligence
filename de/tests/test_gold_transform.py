import numpy as np
import pandas as pd

from epidemiological_de.gold import transform
from epidemiological_de.inmet.transform import aggregate_station_monthly


def _inmet_fixture():
    return pd.DataFrame(
        {
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


# Duas estações em Porto Alegre (431490), uma em Canoas (430460) e uma
# sem município atribuído.
def _station_map_fixture():
    return pd.DataFrame(
        {
            "station_code": ["A801", "B802", "C803", "D804"],
            "municipality_code_6": ["431490", "431490", "430460", None],
        }
    )


def test_aggregate_station_monthly_sums_and_averages_per_station():
    grouped = aggregate_station_monthly(_inmet_fixture())

    station_a801 = grouped[grouped["station_code"] == "A801"].iloc[0]
    assert station_a801["precipitation_sum_mm"] == 10.0
    assert station_a801["precipitation_avg_observation_mm"] == 10.0
    assert station_a801["temperature_avg_c"] == 21.0


def test_aggregate_station_monthly_keeps_null_precipitation_when_all_missing():
    df = _inmet_fixture()
    df.loc[df["station_code"] == "B802", "precipitation_mm"] = np.nan

    grouped = aggregate_station_monthly(df)

    station_b802 = grouped[grouped["station_code"] == "B802"].iloc[0]
    assert pd.isna(station_b802["precipitation_sum_mm"])


def test_attach_municipality_drops_stations_without_municipality():
    station_monthly = aggregate_station_monthly(_inmet_fixture())
    station_monthly = pd.concat(
        [station_monthly, station_monthly.iloc[[0]].assign(station_code="D804")],
        ignore_index=True,
    )

    attached = transform.attach_municipality(station_monthly, _station_map_fixture())

    assert "D804" not in set(attached["station_code"])
    assert set(attached["municipality_code_6"]) == {"431490", "430460"}


def _climate_monthly_fixture():
    station_monthly = aggregate_station_monthly(_inmet_fixture())
    attached = transform.attach_municipality(station_monthly, _station_map_fixture())
    return transform.aggregate_municipality_monthly(attached)


def test_aggregate_municipality_monthly_averages_across_stations_and_counts_them():
    grouped = _climate_monthly_fixture()

    porto_alegre = grouped[grouped["municipality_code"] == "431490"].iloc[0]
    assert porto_alegre["station_count"] == 2
    assert porto_alegre["temperature_avg_c"] == 21.0

    canoas = grouped[grouped["municipality_code"] == "430460"].iloc[0]
    assert canoas["station_count"] == 1


def _sinan_fixture():
    return pd.DataFrame(
        {
            "municipality_code": ["431490", "431490", "430460", "999999"],
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


def test_join_gold_preserves_sinan_row_count():
    sinan_df = _sinan_fixture()
    gold_df = transform.join_gold(sinan_df, _climate_monthly_fixture())

    assert len(gold_df) == len(sinan_df)


def test_join_gold_keeps_epidemiological_record_without_climate_match():
    gold_df = transform.join_gold(_sinan_fixture(), _climate_monthly_fixture())

    missing_climate_row = gold_df[gold_df["municipality"] == "SEM CLIMA"]
    assert len(missing_climate_row) == 1
    assert pd.isna(missing_climate_row.iloc[0]["precipitation_sum_mm"])
    assert missing_climate_row.iloc[0]["cases"] == 1


def test_join_gold_attaches_matching_climate_values():
    gold_df = transform.join_gold(_sinan_fixture(), _climate_monthly_fixture())

    jan_porto_alegre = gold_df[
        (gold_df["municipality"] == "PORTO ALEGRE") & (gold_df["month"] == 1)
    ].iloc[0]
    assert jan_porto_alegre["temperature_avg_c"] == 21.0


def test_join_gold_matches_by_code_not_by_name():
    # Mesmo nome, outro código (homônimo de outra UF): não pode receber
    # o clima de Porto Alegre.
    sinan_df = _sinan_fixture()
    sinan_df.loc[3, ["municipality_code", "municipality"]] = ["999999", "PORTO ALEGRE"]

    gold_df = transform.join_gold(sinan_df, _climate_monthly_fixture())

    homonym = gold_df[gold_df["municipality_code"] == "999999"].iloc[0]
    assert pd.isna(homonym["temperature_avg_c"])


def test_build_gold_has_no_duplicate_disease_municipality_year_month_keys():
    station_monthly = aggregate_station_monthly(_inmet_fixture())
    gold_df = transform.build_gold(station_monthly, _station_map_fixture(), _sinan_fixture())

    duplicate_counts = gold_df.groupby(
        ["disease", "municipality_code", "year", "month"]
    ).size()
    assert (duplicate_counts <= 1).all()


def test_build_gold_preserves_sinan_cardinality_end_to_end():
    sinan_df = _sinan_fixture()
    station_monthly = aggregate_station_monthly(_inmet_fixture())

    gold_df = transform.build_gold(station_monthly, _station_map_fixture(), sinan_df)

    assert len(gold_df) == len(sinan_df)
