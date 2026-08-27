import os
import time
import requests
from datetime import datetime
from airflow.sdk import DAG, task
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")

INMET_JOB_ID = int(os.environ["INMET_JOB_ID"])
SINAN_JOB_ID = int(os.environ["SINAN_JOB_ID"])
GOLD_JOB_ID = int(os.environ["GOLD_JOB_ID"])

def run_databricks_job(job_id: int):
    
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{DATABRICKS_HOST}/api/2.1/jobs/run-now",
        headers=headers,
        json={"job_id": job_id},
        timeout=30,
    )
    response.raise_for_status()
    
    run_id = response.json()["run_id"]
    
    print(f"Job {job_id} started with run_id: {run_id}")
    
    while True:
        response = requests.get(
            f"{DATABRICKS_HOST}/api/2.1/jobs/runs/get",
            headers=headers,
            params={"run_id": run_id},
            timeout=30,
        )
        response.raise_for_status()
        
        run = response.json()
        
        lifecycle_state = run["state"]["life_cycle_state"]
        result_state = run["state"].get("result_state")
        
        print(
            f"run_id: {run_id}, lifecycle_state: {lifecycle_state}, result_state: {result_state}"
        )
        
        if lifecycle_state == "TERMINATED":
            if result_state != "SUCCESS":
                raise RuntimeError(f"Job {job_id} failed with result_state: {result_state}")
            print(f"Job {job_id} completed successfully.")
            return
        if lifecycle_state in [
            "INTERNAL_ERROR",
            "SKIPPED",
        ]:
            raise RuntimeError(
                f"Databricks Job terminou em estado inválido: "
                f"{lifecycle_state}"
            )

        time.sleep(15)
        
with DAG(
    dag_id="epidemiological_intelligence_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["databricks", "epidemiology"],
) as dag:

    @task
    def process_inmet():
        run_databricks_job(INMET_JOB_ID)

    @task
    def process_sinan():
        run_databricks_job(SINAN_JOB_ID)

    @task
    def silver_to_gold():
        run_databricks_job(GOLD_JOB_ID)

    inmet = process_inmet()
    sinan = process_sinan()
    gold = silver_to_gold()
    
    load_gold_bigquery = GCSToBigQueryOperator(
    task_id="load_gold_bigquery",
    bucket="epidemiological-intelligence",
    source_objects=[
        "gold/epidemiology_climate/*.parquet"
    ],
    destination_project_dataset_table=(
        "affable-alpha-506516-r7."
        "epidemiological_intelligence."
        "epidemiology_climate_monthly"
    ),
    source_format="PARQUET",
    write_disposition="WRITE_TRUNCATE",
    autodetect=True,
    gcp_conn_id="google_cloud_default",
    project_id="affable-alpha-506516-r7",
)
    run_data_science = CloudRunExecuteJobOperator(
    task_id="run_data_science",
    project_id="affable-alpha-506516-r7",
    region="us-central1",
    job_name="epidemiological-ds-modeling",
    gcp_conn_id="google_cloud_default",
    deferrable=False,
)

    [inmet, sinan] >> gold >> load_gold_bigquery >> run_data_science
    