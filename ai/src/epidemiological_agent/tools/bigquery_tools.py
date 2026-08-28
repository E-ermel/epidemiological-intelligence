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