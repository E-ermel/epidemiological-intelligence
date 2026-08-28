import pandas as pd


def normalize_municipality(inmet_df: pd.DataFrame) -> pd.DataFrame:

    inmet_df = inmet_df.copy()

    # na=False mantém municípios nulos no ramo "otherwise" do notebook original;
    # sem isso o ~ sobre uma máscara object com NA levanta TypeError.
    is_porto_alegre = (
        inmet_df["municipality"]
        .str.upper()
        .str.startswith("PORTO ALEGRE", na=False)
    )

    inmet_df["municipality_normalized"] = inmet_df["municipality"].where(
        ~is_porto_alegre, "PORTO ALEGRE"
    )

    return inmet_df


def aggregate_station_monthly(inmet_df: pd.DataFrame) -> pd.DataFrame:

    inmet_df = inmet_df.copy()
    inmet_df["year"] = inmet_df["timestamp"].dt.year
    inmet_df["month"] = inmet_df["timestamp"].dt.month

    # dropna=False replica o groupBy do Spark, que mantém chaves nulas
    # (município sem nome, timestamp inválido) como um grupo próprio.
    grouped = inmet_df.groupby(
        ["municipality_normalized", "station_code", "year", "month"],
        as_index=False,
        dropna=False,
    ).agg(
        precipitation_sum_mm=("precipitation_mm", lambda s: s.sum(min_count=1)),
        precipitation_avg_observation_mm=("precipitation_mm", "mean"),
        precipitation_max_observation_mm=("precipitation_mm", "max"),
        temperature_avg_c=("temperature_c", "mean"),
        dew_point_avg_c=("dew_point_temperature_c", "mean"),
        relative_humidity_avg_pct=("relative_humidity_pct", "mean"),
        atmospheric_pressure_avg_mb=("atmospheric_pressure_mb", "mean"),
        wind_speed_avg_ms=("wind_speed_ms", "mean"),
        wind_gust_max_ms=("wind_gust_ms", "max"),
    )

    return grouped


def aggregate_municipality_monthly(station_monthly_df: pd.DataFrame) -> pd.DataFrame:

    # Média das médias por estação, replicando o F.avg sobre colunas já
    # agregadas do notebook original (não é uma média ponderada por observação).
    grouped = station_monthly_df.groupby(
        ["municipality_normalized", "year", "month"],
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

    grouped = grouped.rename(columns={"municipality_normalized": "municipality"})

    return grouped


def join_gold(sinan_df: pd.DataFrame, inmet_monthly_df: pd.DataFrame) -> pd.DataFrame:

    gold_df = sinan_df.merge(
        inmet_monthly_df,
        on=["municipality", "year", "month"],
        how="left",
    )

    return gold_df


def build_gold(inmet_df: pd.DataFrame, sinan_df: pd.DataFrame) -> pd.DataFrame:

    inmet_gold_base = normalize_municipality(inmet_df)
    inmet_station_monthly = aggregate_station_monthly(inmet_gold_base)
    inmet_monthly = aggregate_municipality_monthly(inmet_station_monthly)
    gold_df = join_gold(sinan_df, inmet_monthly)

    return gold_df
