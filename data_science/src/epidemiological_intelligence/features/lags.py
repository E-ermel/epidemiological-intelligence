import pandas as pd


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


def create_climate_lags(
    df: pd.DataFrame,
    lags=(1, 2, 3),
) -> pd.DataFrame:

    df = df.copy()

    # 1. Uma única linha climática por município/data.
    climate_df = (
        df[
            [
                "municipality",
                "reference_date",
                *CLIMATE_COLUMNS,
            ]
        ]
        .drop_duplicates(
            subset=[
                "municipality",
                "reference_date",
            ]
        )
        .sort_values(
            [
                "municipality",
                "reference_date",
            ]
        )
        .copy()
    )

    # 2. Criar lags dentro de cada município.
    for column in CLIMATE_COLUMNS:
        for lag in lags:

            climate_df[
                f"{column}_lag{lag}"
            ] = (
                climate_df
                .groupby("municipality")[column]
                .shift(lag)
            )

    # 3. Manter somente chaves + novas features.
    lag_columns = [
        column
        for column in climate_df.columns
        if "_lag" in column
    ]

    climate_lags = climate_df[
        [
            "municipality",
            "reference_date",
            *lag_columns,
        ]
    ]

    # 4. Merge de volta no dataframe epidemiológico.
    result = df.merge(
        climate_lags,
        on=[
            "municipality",
            "reference_date",
        ],
        how="left",
        validate="many_to_one",
    )

    return result