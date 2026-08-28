import pandas as pd

def prepare_model_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["reference_date"] = pd.to_datetime(
        df["reference_date"]
    )

    if df["reference_date"].dt.tz is not None:
        df["reference_date"] = df["reference_date"].dt.tz_localize(None)

    df["cases"] = pd.to_numeric(
        df["cases"],
        errors="coerce"
    )

    df["month"] = df["reference_date"].dt.month.astype(int)

    df = df.sort_values(
        ["disease", "municipality", "reference_date"]
    ).reset_index(drop=True)

    return df