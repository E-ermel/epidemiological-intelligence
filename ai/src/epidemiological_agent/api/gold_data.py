import time

import pandas as pd

from epidemiological_agent.tools.bigquery_tools import query_epidemiological_data

# /overview, /geo/*, /studies and /models all load the whole table on
# every request -- in practice that's a real BigQuery scan plus a cold
# client per call, 20+ seconds observed against the live table, not
# the "cheap" in-memory read this comment used to assume. A short TTL
# cache turns every request after the first (within the window) into
# an in-process dict lookup. The Gold table only changes when the DE
# pipeline runs (at most a few times a day), so a few minutes of
# staleness is a non-issue.
_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def load_gold_dataframe() -> pd.DataFrame:
    """
    Load the whole Gold table once, prepped for in-memory aggregation,
    cached for _CACHE_TTL_SECONDS.
    """

    cached = _cache.get("gold")

    if cached is not None:
        cached_at, cached_df = cached

        if time.time() - cached_at < _CACHE_TTL_SECONDS:
            return cached_df.copy()

    df = query_epidemiological_data()
    df["reference_date"] = pd.to_datetime(df["reference_date"])
    df["cases"] = pd.to_numeric(df["cases"], errors="coerce")

    _cache["gold"] = (time.time(), df)

    return df.copy()
