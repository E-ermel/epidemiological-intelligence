import numpy as np
import pandas as pd
import pytest

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
            "latitude": [-30.05, -30.10, -29.92, -29.00],
            "longitude": [-51.17, -51.20, -51.18, -50.00],
        }
    )


# Porto Alegre e Canoas têm estação; Gravataí (~20 km) não; Uruguaiana
# (~600 km) não tem nenhuma por perto; Boa Esperança do Norte não tem
# centróide.
DIM = pd.DataFrame(
    {
        "municipality_code": ["4314902", "4304606", "4309209", "4322400", "5101837"],
        "municipality_code_6": ["431490", "430460", "430920", "432240", "510183"],
        "municipality_name": ["Porto Alegre", "Canoas", "Gravataí", "Uruguaiana", "Boa Esperança do Norte"],
        "municipality_name_normalized": ["PORTO ALEGRE", "CANOAS", "GRAVATAI", "URUGUAIANA", "BOA ESPERANCA DO NORTE"],
        "state": ["RS", "RS", "RS", "RS", "MT"],
        "region": ["S", "S", "S", "S", "CO"],
        "latitude": [-30.03, -29.92, -29.94, -29.75, None],
        "longitude": [-51.23, -51.18, -50.99, -57.09, None],
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


def test_aggregate_municipality_monthly_averages_across_stations_and_counts_them():
    attached = transform.attach_municipality(aggregate_station_monthly(_inmet_fixture()), _station_map_fixture())
    grouped = transform.aggregate_municipality_monthly(attached)

    porto_alegre = grouped[grouped["municipality_code"] == "431490"].iloc[0]
    assert porto_alegre["station_count"] == 2
    assert porto_alegre["temperature_avg_c"] == 21.0

    canoas = grouped[grouped["municipality_code"] == "430460"].iloc[0]
    assert canoas["station_count"] == 1


# ---------------------------------------------------------------------
# Clima por município (estação própria ou mais próxima)
# ---------------------------------------------------------------------


def test_haversine_matrix_matches_known_distance():
    # Porto Alegre -> Uruguaiana: ~570 km em linha reta.
    distance = transform.haversine_matrix_km([-30.03], [-51.23], [-29.75], [-57.09])[0, 0]

    assert distance == pytest.approx(566, abs=10)


def _climate():
    return transform.municipality_climate(
        aggregate_station_monthly(_inmet_fixture()), _station_map_fixture(), DIM, max_distance_km=100
    ).set_index("municipality_code")


def test_municipality_with_station_uses_its_own():
    climate = _climate()

    assert climate.loc["431490", "climate_source"] == transform.OWN_STATION
    assert climate.loc["431490", "climate_distance_km"] == 0
    assert climate.loc["431490", "temperature_avg_c"] == 21.0


def test_municipality_without_station_borrows_the_nearest_with_data():
    climate = _climate()

    gravatai = climate.loc["430920"]
    assert gravatai["climate_source"] == transform.NEAREST_STATION
    # C803 (Canoas) é a mais próxima de Gravataí.
    assert gravatai["temperature_avg_c"] == 18.0
    assert 0 < gravatai["climate_distance_km"] < 30


def test_no_climate_beyond_max_distance_or_without_centroid():
    climate = _climate()

    assert "432240" not in climate.index  # Uruguaiana
    assert "510183" not in climate.index  # sem centróide


def test_nearest_skips_station_without_data_that_month():
    monthly = aggregate_station_monthly(_inmet_fixture())
    monthly.loc[monthly["station_code"] == "C803", transform.CLIMATE_COLUMNS] = np.nan

    climate = transform.municipality_climate(monthly, _station_map_fixture(), DIM, 100).set_index("municipality_code")

    # Sem C803 no mês: Canoas e Gravataí pegam a estação seguinte (Porto Alegre).
    assert climate.loc["430460", "climate_source"] == transform.NEAREST_STATION
    assert climate.loc["430920", "temperature_avg_c"] in (21.0, 22.0, 20.0)


# ---------------------------------------------------------------------
# Casos e gold
# ---------------------------------------------------------------------


SILVER = pd.DataFrame(
    {
        "disease": ["ASMA", "ASMA", "ASMA", "ASMA"],
        # Residente de Gravataí internado em Porto Alegre; um de Porto
        # Alegre lá mesmo; um código ignorado (430000).
        "residence_municipality_code": ["430920", "431490", "430000", "431490"],
        "occurrence_municipality_code": ["431490", "431490", "431490", "431490"],
        "year": [2023, 2023, 2023, 2023],
        "month": [1, 1, 1, 2],
        "hospitalizations": [3, 5, 1, 2],
        "is_provisional": [False, False, False, True],
    }
)


def test_case_counts_by_residence_and_by_occurrence():
    counts = transform.case_counts(SILVER, "hospitalizations").set_index(["municipality_code", "month"])

    assert counts.loc[("431490", 1), "cases"] == 5
    assert counts.loc[("431490", 1), "cases_by_occurrence"] == 9
    assert counts.loc[("430920", 1), "cases"] == 3
    assert pd.isna(counts.loc[("430920", 1), "cases_by_occurrence"])


def test_month_range_goes_from_first_year_to_last_month_with_data():
    months = transform.month_range(SILVER, first_year=2022)

    assert len(months) == 14
    assert months.iloc[-1].tolist() == [2023, 2]


def _gold():
    return transform.build_disease_gold(
        "ASMA",
        "SIH",
        transform.case_counts(SILVER, "hospitalizations"),
        transform.month_range(SILVER, first_year=2023),
        transform.provisional_months(SILVER),
        DIM,
        transform.municipality_climate(aggregate_station_monthly(_inmet_fixture()), _station_map_fixture(), DIM, 100),
    )


def test_gold_has_one_row_per_municipality_and_month_with_explicit_zeros():
    gold = _gold()

    assert list(gold.columns) == transform.GOLD_COLUMNS
    assert len(gold) == len(DIM) * 2
    assert not gold.duplicated(["municipality_code", "year", "month"]).any()

    canoas = gold[(gold["municipality_code"] == "430460") & (gold["month"] == 1)].iloc[0]
    assert canoas["cases"] == 0
    assert canoas["cases_by_occurrence"] == 0


def test_gold_carries_names_codes_flags_and_climate():
    gold = _gold().set_index(["municipality_code", "month"])

    gravatai = gold.loc[("430920", 1)]
    assert gravatai["ibge_code"] == "4309209"
    assert gravatai["municipality"] == "GRAVATAI"
    assert gravatai["municipality_name"] == "Gravataí"
    assert gravatai["cases"] == 3
    assert gravatai["climate_source"] == transform.NEAREST_STATION

    assert bool(gold.loc[("431490", 2), "is_provisional"]) is True
    assert bool(gold.loc[("431490", 1), "is_provisional"]) is False
    assert gold.loc[("431490", 1), "reference_date"] == pd.Timestamp("2023-01-01", tz="UTC")


def test_gold_drops_unknown_municipality_codes():
    gold = _gold()

    assert "430000" not in set(gold["municipality_code"])
    assert gold["cases"].sum() == 3 + 5 + 2
