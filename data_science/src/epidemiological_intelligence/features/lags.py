import pandas as pd

def create_lags(
    df: pd.DataFrame,
    columns: list[str],
    lags: tuple[int, ...] = (1, 2, 3),
) -> pd.DataFrame:
    df = df.copy()

    df = df.sort_values(
        ["municipality", "reference_date"]
    )
    for column in columns:
        for lag in lags:
            df[f"{column}_lag_{lag}"] = (
                df.groupby("municipality")[column]
                .shift(lag)
            )

    return df