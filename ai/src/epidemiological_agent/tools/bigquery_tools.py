import time
from functools import lru_cache

import pandas as pd
from google.cloud import bigquery

from epidemiological_agent.config import (
    PROJECT_ID,
    BIGQUERY_DATASET,
    BIGQUERY_TABLE
)


@lru_cache(maxsize=1)
def _get_bigquery_client() -> bigquery.Client:
    # Constructing a client does credential discovery on every call;
    # bigquery.Client is documented safe to reuse across queries.
    return bigquery.Client(project=PROJECT_ID)


# Same TTL-cache shape as gold_data.py's load_gold_dataframe -- the
# Gold table only advances when the DE pipeline runs, so a few
# minutes of staleness on "what's the latest date" is a non-issue.
_MAX_DATE_CACHE_TTL_SECONDS = 300
_max_date_cache: dict[str, tuple[float, pd.Timestamp | None]] = {}


def get_max_reference_date() -> pd.Timestamp | None:
    """
    Most recent reference_date present in the Gold table.

    Used to tell apart a request for a period the project genuinely
    has no data for (e.g. the user asking about 2026 when records
    stop in 2025) from an ordinary empty filter combination.
    """

    cached = _max_date_cache.get("max_date")

    if cached is not None:
        cached_at, cached_value = cached

        if time.time() - cached_at < _MAX_DATE_CACHE_TTL_SECONDS:
            return cached_value

    client = _get_bigquery_client()

    table = (
        f"{PROJECT_ID}."
        f"{BIGQUERY_DATASET}."
        f"{BIGQUERY_TABLE}"
    )

    row = next(
        client
        .query(f"SELECT MAX(reference_date) AS max_date FROM `{table}`")
        .result()
    )

    max_date = row["max_date"]

    if max_date is not None:
        max_date = pd.Timestamp(max_date)

    _max_date_cache["max_date"] = (time.time(), max_date)

    return max_date


def query_epidemiological_data(
    disease: str | None = None,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:

    client = _get_bigquery_client()

    table = (
        f"{PROJECT_ID}."
        f"{BIGQUERY_DATASET}."
        f"{BIGQUERY_TABLE}"
    )
    
    query = f"""
        SELECT 
            reference_date,
            disease,
            municipality,
            cases,
            precipitation_sum_mm,
            precipitation_max_observation_mm,
            temperature_avg_c,
            dew_point_avg_c,
            relative_humidity_avg_pct,
            atmospheric_pressure_avg_mb,
            wind_speed_avg_ms,
            wind_gust_max_ms
        FROM `{table}`
        WHERE 1 = 1
    """
    
    parameters = []
    
    if disease is not None:
        query += """
            AND UPPER(disease) = UPPER(@disease)
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "disease",
                "STRING",
                disease,
            )
        )
        
    if municipality is not None:
        query += """ AND UPPER(municipality) = UPPER(@municipality)"""
        
        parameters.append(
            bigquery.ScalarQueryParameter(
                "municipality", "STRING", municipality
            )
        )
        
    if start_date is not None:
        query += """
            AND reference_date >= @start_date
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "start_date",
                "TIMESTAMP",
                start_date,
            )
        )

    if end_date is not None:
        query += """
            AND reference_date <= @end_date
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "end_date",
                "TIMESTAMP",
                end_date,
            )
        )

    query += """
        ORDER BY
            municipality,
            reference_date
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=parameters
    )
    
    result = client.query(query, job_config=job_config)
    
    return result.to_dataframe()

def get_total_cases(
    disease: str,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> int:

    client = _get_bigquery_client()

    table = (
        f"{PROJECT_ID}."
        f"{BIGQUERY_DATASET}."
        f"{BIGQUERY_TABLE}"
    )

    query = f"""
        SELECT
            SUM(cases) AS total_cases
        FROM `{table}`
        WHERE 1 = 1
    """

    parameters = []

    if disease is not None:
        query += """
            AND UPPER(disease) = UPPER(@disease)
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "disease",
                "STRING",
                disease,
            )
        )

    if municipality is not None:
        query += """
            AND UPPER(municipality) = UPPER(@municipality)
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "municipality",
                "STRING",
                municipality,
            )
        )

    if start_date is not None:
        query += """
            AND reference_date >= @start_date
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "start_date",
                "TIMESTAMP",
                start_date,
            )
        )

    if end_date is not None:
        query += """
            AND reference_date <= @end_date
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "end_date",
                "TIMESTAMP",
                end_date,
            )
        )

    job_config = bigquery.QueryJobConfig(
        query_parameters=parameters
    )

    result = (
        client
        .query(
            query,
            job_config=job_config,
        )
        .result()
    )

    row = next(result)

    return int(
        row["total_cases"] or 0
    )


_CLIMATE_COLUMNS = [
    "precipitation_sum_mm",
    "precipitation_max_observation_mm",
    "temperature_avg_c",
    "dew_point_avg_c",
    "relative_humidity_avg_pct",
    "atmospheric_pressure_avg_mb",
    "wind_speed_avg_ms",
    "wind_gust_max_ms",
]


def get_climate_summary(
    disease: str | None = None,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Aggregated (avg/min/max) climate stats over the matching rows --
    the tool-facing counterpart to get_total_cases, so the agent
    doesn't have to average a raw JSON record list itself (see
    epidemiological_data_tool, which returns un-aggregated monthly
    records).

    Climate columns are duplicated per disease for the same
    municipality/month (one Gold row per disease), so aggregating
    straight off the table would double-count a reading once per
    disease present that month. The DISTINCT in the CTE below
    collapses that back to one row per municipality/month before
    aggregating -- a no-op when `disease` is already given, since
    then there's only one disease's rows to begin with.
    """

    client = _get_bigquery_client()

    table = (
        f"{PROJECT_ID}."
        f"{BIGQUERY_DATASET}."
        f"{BIGQUERY_TABLE}"
    )

    select_clause = ",\n            ".join(
        f"AVG({column}) AS {column}_avg, "
        f"MIN({column}) AS {column}_min, "
        f"MAX({column}) AS {column}_max"
        for column in _CLIMATE_COLUMNS
    )

    query = f"""
        WITH climate_rows AS (
            SELECT DISTINCT
                municipality,
                reference_date,
                {", ".join(_CLIMATE_COLUMNS)}
            FROM `{table}`
            WHERE 1 = 1
    """

    parameters = []

    if disease is not None:
        query += """
            AND UPPER(disease) = UPPER(@disease)
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "disease",
                "STRING",
                disease,
            )
        )

    if municipality is not None:
        query += """
            AND UPPER(municipality) = UPPER(@municipality)
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "municipality", "STRING", municipality
            )
        )

    if start_date is not None:
        query += """
            AND reference_date >= @start_date
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "start_date",
                "TIMESTAMP",
                start_date,
            )
        )

    if end_date is not None:
        query += """
            AND reference_date <= @end_date
        """

        parameters.append(
            bigquery.ScalarQueryParameter(
                "end_date",
                "TIMESTAMP",
                end_date,
            )
        )

    query += f"""
        )
        SELECT
            {select_clause}
        FROM climate_rows
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=parameters
    )

    result = (
        client
        .query(
            query,
            job_config=job_config,
        )
        .result()
    )

    row = next(result)

    def _none_or_float(value):
        return None if value is None else float(value)

    return {
        column: {
            "avg": _none_or_float(row[f"{column}_avg"]),
            "min": _none_or_float(row[f"{column}_min"]),
            "max": _none_or_float(row[f"{column}_max"]),
        }
        for column in _CLIMATE_COLUMNS
    }