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

# Alerta de surtos, gravado pelo job epidemiological-ds-alert: linhas no
# BigQuery e o resumo da rodada (modelo, cortes, métricas) no GCS.
BIGQUERY_ALERT_TABLE = os.getenv("BIGQUERY_ALERT_TABLE", "outbreak_alerts")

ARTIFACT_BUCKET = os.getenv("ARTIFACT_BUCKET", "epidemiological-intelligence")

ALERT_ARTIFACT_PREFIX = os.getenv("ALERT_ARTIFACT_PREFIX", "alert")

# .strip() matters here specifically: a trailing newline copy-pasted into
# a .env file or a terminal `$env:` assignment makes the Authorization
# header itself invalid (`Bearer sk-...\n`), which surfaces as an opaque
# httpcore "Illegal header value" / connection error, not an auth error --
# very easy to mistake for a code bug.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()