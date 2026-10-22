import pandas as pd


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


def join_gold(sinan_df: pd.DataFrame, climate_monthly_df: pd.DataFrame) -> pd.DataFrame:

    # Por código, não por nome: no Brasil inteiro há municípios
    # homônimos em UFs diferentes (ex.: Santa Maria/RS e Santa Maria/RN).
    gold_df = sinan_df.merge(
        climate_monthly_df,
        on=["municipality_code", "year", "month"],
        how="left",
    )

    return gold_df


def build_gold(
    station_monthly_df: pd.DataFrame,
    station_map_df: pd.DataFrame,
    sinan_df: pd.DataFrame,
) -> pd.DataFrame:

    with_municipality = attach_municipality(station_monthly_df, station_map_df)
    climate_monthly = aggregate_municipality_monthly(with_municipality)
    gold_df = join_gold(sinan_df, climate_monthly)

    return gold_df
