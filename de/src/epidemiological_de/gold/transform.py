"""
Gold nacional: município × mês × doença, com clima.

- Uma linha para cada município da dim_municipality, cada mês e cada
  doença, com zero onde não houve caso -- o modelo precisa dos zeros.
- `cases` conta pelo município de residência; `cases_by_occurrence`
  pelo local do evento (internação no SIH; infecção/acidente no SINAN).
- Clima: média das estações do próprio município; sem dado próprio
  naquele mês, a estação mais próxima com dado, até
  config.CLIMATE_MAX_DISTANCE_KM. `climate_source` e
  `climate_distance_km` dizem de onde veio.
"""

import numpy as np
import pandas as pd

from epidemiological_de.atlas.transform import GOLD_FEATURES as ATLAS_FEATURES
from epidemiological_de.mapbiomas.transform import GOLD_FEATURES as LAND_COVER_COLUMNS
from epidemiological_de.prodes.transform import GOLD_FEATURES as DEFORESTATION_COLUMNS

# Características fixas do município (censo 2010, Atlas Brasil).
ATLAS_COLUMNS = [f"atlas_{feature}" for feature in ATLAS_FEATURES]

POPULATION_COLUMNS = ["population", "population_density"]

CLIMATE_COLUMNS = [
    "precipitation_sum_mm",
    "precipitation_avg_observation_mm",
    "precipitation_max_observation_mm",
    "temperature_avg_c",
    "dew_point_avg_c",
    "relative_humidity_avg_pct",
    "atmospheric_pressure_avg_mb",
    "wind_speed_avg_ms",
    "wind_gust_max_ms",
]

GOLD_COLUMNS = [
    "municipality_code",
    "ibge_code",
    "municipality",
    "municipality_name",
    "state",
    "region",
    "disease",
    "source",
    "year",
    "month",
    "reference_date",
    "cases",
    "cases_by_occurrence",
    "is_provisional",
    *POPULATION_COLUMNS,
    *LAND_COVER_COLUMNS,
    *DEFORESTATION_COLUMNS,
    *ATLAS_COLUMNS,
    *CLIMATE_COLUMNS,
    "station_count",
    "climate_source",
    "climate_distance_km",
]

KEYS = ["municipality_code", "year", "month"]

OWN_STATION = "own_station"
NEAREST_STATION = "nearest_station"


# ---------------------------------------------------------------------
# Clima
# ---------------------------------------------------------------------


def attach_municipality(
    station_monthly_df: pd.DataFrame,
    station_map_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Liga cada estação ao seu município (inmet/stations.py). Estação sem
    município atribuído fica de fora: não há com o que cruzar.
    """

    station_map = station_map_df[["station_code", "municipality_code_6"]].dropna()

    return station_monthly_df.merge(
        station_map,
        on="station_code",
        how="inner",
        validate="many_to_one",
    )


def aggregate_municipality_monthly(station_monthly_df: pd.DataFrame) -> pd.DataFrame:

    # Média das médias por estação, replicando o F.avg sobre colunas já
    # agregadas do notebook original (não é uma média ponderada por observação).
    grouped = station_monthly_df.groupby(
        ["municipality_code_6", "year", "month"],
        as_index=False,
        dropna=False,
    ).agg(
        precipitation_sum_mm=("precipitation_sum_mm", "mean"),
        precipitation_avg_observation_mm=("precipitation_avg_observation_mm", "mean"),
        precipitation_max_observation_mm=("precipitation_max_observation_mm", "max"),
        temperature_avg_c=("temperature_avg_c", "mean"),
        dew_point_avg_c=("dew_point_avg_c", "mean"),
        relative_humidity_avg_pct=("relative_humidity_avg_pct", "mean"),
        atmospheric_pressure_avg_mb=("atmospheric_pressure_avg_mb", "mean"),
        wind_speed_avg_ms=("wind_speed_avg_ms", "mean"),
        wind_gust_max_ms=("wind_gust_max_ms", "max"),
        station_count=("station_code", "nunique"),
    )

    # O SINAN/SIH (DATASUS) identifica o município pelo código de 6
    # dígitos, na coluna municipality_code -- mesmo nome para o join.
    return grouped.rename(columns={"municipality_code_6": "municipality_code"})


def haversine_matrix_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Distâncias (km) de cada ponto 1 (linhas) a cada ponto 2 (colunas)."""

    lat1, lon1 = np.radians(np.asarray(lat1, float))[:, None], np.radians(np.asarray(lon1, float))[:, None]
    lat2, lon2 = np.radians(np.asarray(lat2, float))[None, :], np.radians(np.asarray(lon2, float))[None, :]

    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def station_candidates(dim: pd.DataFrame, station_map: pd.DataFrame, max_distance_km: float) -> pd.DataFrame:
    """
    Pares (município, estação) a até `max_distance_km` do centróide do
    município, com a distância. Município sem centróide fica sem par.
    """

    municipalities = dim.dropna(subset=["latitude", "longitude"])
    stations = station_map.dropna(subset=["latitude", "longitude"])

    distances = haversine_matrix_km(
        municipalities["latitude"], municipalities["longitude"],
        stations["latitude"], stations["longitude"],
    )
    rows, cols = np.nonzero(distances <= max_distance_km)

    return pd.DataFrame(
        {
            "municipality_code": municipalities["municipality_code_6"].to_numpy()[rows],
            "station_code": stations["station_code"].to_numpy()[cols],
            "distance_km": distances[rows, cols].round(1),
        }
    )


def _has_climate(station_monthly: pd.DataFrame) -> pd.Series:
    return station_monthly[CLIMATE_COLUMNS].notna().any(axis=1)


def nearest_station_climate(station_monthly: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    """Para cada município e mês, o clima da estação candidata mais próxima que tem dado naquele mês."""

    available = station_monthly.loc[_has_climate(station_monthly), ["station_code", "year", "month"]]

    nearest = (
        candidates.merge(available, on="station_code")
        .sort_values(["municipality_code", "year", "month", "distance_km", "station_code"])
        .drop_duplicates(KEYS, keep="first")
    )

    return nearest.merge(
        station_monthly[["station_code", "year", "month", *CLIMATE_COLUMNS]],
        on=["station_code", "year", "month"],
        how="left",
    ).drop(columns="station_code").rename(columns={"distance_km": "climate_distance_km"})


def municipality_climate(
    station_monthly: pd.DataFrame,
    station_map: pd.DataFrame,
    dim: pd.DataFrame,
    max_distance_km: float,
) -> pd.DataFrame:
    """Uma linha por município × mês com clima: estação própria, ou a mais próxima."""

    own = aggregate_municipality_monthly(
        attach_municipality(station_monthly[_has_climate(station_monthly)], station_map)
    ).assign(climate_source=OWN_STATION, climate_distance_km=0.0)

    nearest = nearest_station_climate(
        station_monthly, station_candidates(dim, station_map, max_distance_km)
    ).assign(climate_source=NEAREST_STATION, station_count=1)

    # Estação própria tem prioridade; a mais próxima só cobre o resto.
    nearest = nearest.merge(own[KEYS], on=KEYS, how="left", indicator=True)
    nearest = nearest[nearest["_merge"] == "left_only"].drop(columns="_merge")

    climate = pd.concat([own, nearest], ignore_index=True)
    return climate.astype({"year": "int64", "month": "int64", "station_count": "int64"})


# ---------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------


def case_counts(silver: pd.DataFrame, count_column: str) -> pd.DataFrame:
    """
    Silver (doença × residência × evento × mês) -> doença × município ×
    mês, com `cases` (residência) e `cases_by_occurrence` (evento).
    """

    keys = ["disease", "year", "month"]

    by_residence = (
        silver.dropna(subset=["residence_municipality_code"])
        .groupby([*keys, "residence_municipality_code"], as_index=False)[count_column].sum()
        .rename(columns={"residence_municipality_code": "municipality_code", count_column: "cases"})
    )
    by_occurrence = (
        silver.dropna(subset=["occurrence_municipality_code"])
        .groupby([*keys, "occurrence_municipality_code"], as_index=False)[count_column].sum()
        .rename(columns={"occurrence_municipality_code": "municipality_code", count_column: "cases_by_occurrence"})
    )

    return by_residence.merge(by_occurrence, on=[*keys, "municipality_code"], how="outer")


def provisional_months(silver: pd.DataFrame) -> pd.DataFrame:
    """(ano, mês) provisórios de uma fonte: algum registro do mês ainda pode mudar."""

    return silver.groupby(["year", "month"], as_index=False)["is_provisional"].any()


def month_range(silver: pd.DataFrame, first_year: int) -> pd.DataFrame:
    """Todos os meses de janeiro de `first_year` até o último mês com dado na fonte."""

    last = silver.loc[(silver["year"] * 12 + silver["month"]).idxmax(), ["year", "month"]]
    months = pd.period_range(f"{first_year}-01", f"{int(last['year'])}-{int(last['month']):02d}", freq="M")

    return pd.DataFrame({"year": months.year.astype("int64"), "month": months.month.astype("int64")})


# ---------------------------------------------------------------------
# Gold
# ---------------------------------------------------------------------


def build_disease_gold(
    disease: str,
    source: str,
    counts: pd.DataFrame,
    months: pd.DataFrame,
    provisional: pd.DataFrame,
    dim: pd.DataFrame,
    climate: pd.DataFrame,
    yearly_features: list[pd.DataFrame],
    static_features: list[pd.DataFrame],
) -> pd.DataFrame:
    """
    Grade município × mês de uma doença. Casos de códigos que não estão
    na dim_municipality (ignorado, "999999"...) ficam de fora.

    - `yearly_features`: tabelas com municipality_code_6, year e as
      colunas da característica (população, uso do solo...); o valor do
      ano se repete nos 12 meses.
    - `static_features`: tabelas com municipality_code_6 e as colunas
      (IDHM do censo 2010...); o mesmo valor em todos os meses.

    Município ou ano sem valor na característica fica nulo, não zero.
    """

    municipalities = dim[["municipality_code_6", "municipality_code", "municipality_name_normalized",
                          "municipality_name", "state", "region"]].rename(
        columns={
            "municipality_code": "ibge_code",
            "municipality_code_6": "municipality_code",
            "municipality_name_normalized": "municipality",
        }
    )

    grid = municipalities.merge(months, how="cross")

    disease_counts = counts.loc[counts["disease"] == disease].drop(columns="disease")
    gold = grid.merge(disease_counts, on=KEYS, how="left", validate="one_to_one")
    gold[["cases", "cases_by_occurrence"]] = gold[["cases", "cases_by_occurrence"]].fillna(0).astype("int64")

    gold = gold.merge(provisional, on=["year", "month"], how="left")
    gold["is_provisional"] = gold["is_provisional"].fillna(False).astype(bool)

    for features in yearly_features:
        gold = gold.merge(
            features.rename(columns={"municipality_code_6": "municipality_code"}),
            on=["municipality_code", "year"],
            how="left",
            validate="many_to_one",
        )

    for features in static_features:
        gold = gold.merge(
            features.rename(columns={"municipality_code_6": "municipality_code"}),
            on="municipality_code",
            how="left",
            validate="many_to_one",
        )

    gold = gold.merge(climate, on=KEYS, how="left", validate="many_to_one")
    gold["station_count"] = gold["station_count"].fillna(0).astype("int64")

    gold["disease"] = disease
    gold["source"] = source
    # UTC e microssegundos: no parquet, timestamp sem fuso vira DATETIME
    # no BigQuery (a tabela anterior tinha TIMESTAMP) e nanossegundos não
    # são aceitos.
    gold["reference_date"] = (
        pd.to_datetime({"year": gold["year"], "month": gold["month"], "day": 1})
        .astype("datetime64[us]")
        .dt.tz_localize("UTC")
    )

    return gold[GOLD_COLUMNS]
