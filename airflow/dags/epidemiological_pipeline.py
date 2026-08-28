import os
from datetime import datetime

from airflow.sdk import DAG
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import (
    GCSToBigQueryOperator,
)
from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)


# -------------------------------------------------------------------
# Configuração
# -------------------------------------------------------------------

PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "affable-alpha-506516-r7",
)

REGION = os.getenv(
    "GCP_REGION",
    "us-central1",
)

BUCKET_NAME = os.getenv(
    "ARTIFACT_BUCKET",
    "epidemiological-intelligence",
)

BIGQUERY_DATASET = os.getenv(
    "BIGQUERY_DATASET",
    "epidemiological_intelligence",
)

BIGQUERY_GOLD_TABLE = os.getenv(
    "BIGQUERY_GOLD_TABLE",
    "epidemiology_climate_monthly",
)

GCP_CONN_ID = "google_cloud_default"


# -------------------------------------------------------------------
# DAG
# -------------------------------------------------------------------

with DAG(
    dag_id="epidemiological_intelligence_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=[
        "cloud-run",
        "data-engineering",
        "data-science",
        "epidemiology",
    ],
) as dag:

    # ---------------------------------------------------------------
    # Data Engineering - Bronze -> Silver
    # ---------------------------------------------------------------

    process_inmet = CloudRunExecuteJobOperator(
        task_id="process_inmet",
        project_id=PROJECT_ID,
        region=REGION,
        job_name="epidemiological-de-inmet",
        gcp_conn_id=GCP_CONN_ID,
        deferrable=False,
    )

    process_sinan = CloudRunExecuteJobOperator(
        task_id="process_sinan",
        project_id=PROJECT_ID,
        region=REGION,
        job_name="epidemiological-de-sinan",
        gcp_conn_id=GCP_CONN_ID,
        deferrable=False,
    )

    # ---------------------------------------------------------------
    # Data Engineering - Silver -> Gold
    # ---------------------------------------------------------------

    silver_to_gold = CloudRunExecuteJobOperator(
        task_id="silver_to_gold",
        project_id=PROJECT_ID,
        region=REGION,
        job_name="epidemiological-de-gold",
        gcp_conn_id=GCP_CONN_ID,
        deferrable=False,
    )

    # ---------------------------------------------------------------
    # Gold -> BigQuery
    # ---------------------------------------------------------------

    load_gold_bigquery = GCSToBigQueryOperator(
        task_id="load_gold_bigquery",
        bucket=BUCKET_NAME,
        source_objects=[
            "gold/epidemiology_climate/*.parquet",
        ],
        destination_project_dataset_table=(
            f"{PROJECT_ID}."
            f"{BIGQUERY_DATASET}."
            f"{BIGQUERY_GOLD_TABLE}"
        ),
        source_format="PARQUET",
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
        gcp_conn_id=GCP_CONN_ID,
        project_id=PROJECT_ID,
    )

    # ---------------------------------------------------------------
    # Data Science
    # ---------------------------------------------------------------

    run_data_science = CloudRunExecuteJobOperator(
        task_id="run_data_science",
        project_id=PROJECT_ID,
        region=REGION,
        job_name="epidemiological-ds-modeling",
        gcp_conn_id=GCP_CONN_ID,
        deferrable=False,
    )

    # ---------------------------------------------------------------
    # Dependências
    # ---------------------------------------------------------------

    [process_inmet, process_sinan] >> silver_to_gold

    silver_to_gold >> load_gold_bigquery >> run_data_science