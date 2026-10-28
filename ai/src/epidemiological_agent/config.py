import os

PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "affable-alpha-506516-r7",
)

BIGQUERY_DATASET = os.getenv(
    "BIGQUERY_DATASET",
    "epidemiological_intelligence",
)

# Gold nacional. O Cloud Run injeta BIGQUERY_GOLD_TABLE (cloud_run.tf);
# BIGQUERY_TABLE fica como alternativa para rodar localmente.
BIGQUERY_TABLE = os.getenv(
    "BIGQUERY_GOLD_TABLE",
    os.getenv("BIGQUERY_TABLE", "epidemiology_climate_monthly_br"),
)

# Municípios do IBGE (código, nome, UF, centróide): carregada pelo
# pipeline de DE junto com o gold.
BIGQUERY_DIM_MUNICIPALITY_TABLE = os.getenv(
    "BIGQUERY_DIM_MUNICIPALITY_TABLE",
    "dim_municipality",
)

# Deployed values (infrastructure/terraform/cloud_run.tf) -- the "ai"
# Cloud Run service gets these injected, but local dev usually doesn't
# set them, which made POST /models/{disease}/retrain crash with an
# unhandled KeyError instead of a clean error. Defaulting to the real
# deployed region/job name fixes local retraining too.
GCP_REGION = os.getenv("GCP_REGION", "us-central1")

DS_JOB_NAME = os.getenv("DS_JOB_NAME", "epidemiological-ds-modeling")

# .strip() matters here specifically: a trailing newline copy-pasted into
# a .env file or a terminal `$env:` assignment makes the Authorization
# header itself invalid (`Bearer sk-...\n`), which surfaces as an opaque
# httpcore "Illegal header value" / connection error, not an auth error --
# very easy to mistake for a code bug.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()