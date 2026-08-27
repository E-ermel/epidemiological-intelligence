import os

PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "affable-alpha-506516-r7",
)

BIGQUERY_DATASET = os.getenv(
    "BIGQUERY_DATASET",
    "epidemiological_intelligence",
)

BIGQUERY_TABLE = os.getenv(
    "BIGQUERY_TABLE",
    "epidemiology_climate_monthly",
)