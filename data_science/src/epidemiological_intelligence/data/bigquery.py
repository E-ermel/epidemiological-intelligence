import os

import pandas as pd
from google.cloud import bigquery


def load_gold_from_bigquery() -> pd.DataFrame:
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv(
        "BIGQUERY_DATASET",
        "epidemiological_intelligence",
    )
    table_id = os.getenv(
        "BIGQUERY_GOLD_TABLE",
        "epidemiology_climate",
    )

    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID não foi definido."
        )

    client = bigquery.Client(
        project=project_id
    )

    query = f"""
        SELECT *
        FROM `{project_id}.{dataset_id}.{table_id}`
    """

    df = client.query(
        query
    ).to_dataframe()

    return df