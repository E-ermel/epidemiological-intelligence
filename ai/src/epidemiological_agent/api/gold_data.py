import pandas as pd

from epidemiological_agent.tools.bigquery_tools import query_epidemiological_data


def load_gold_dataframe() -> pd.DataFrame:
    """
    Load the whole Gold table once, prepped for in-memory aggregation.

    overview/geo/studies all need the same base data. Calling
    query_epidemiological_data() with no filters returns the full
    table -- cheap here because the Gold table is already
    monthly-aggregated, not row-level.
    """

    df = query_epidemiological_data()
    df["reference_date"] = pd.to_datetime(df["reference_date"])
    df["cases"] = pd.to_numeric(df["cases"], errors="coerce")
    return df
