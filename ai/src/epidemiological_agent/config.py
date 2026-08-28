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

# .strip() matters here specifically: a trailing newline copy-pasted into
# a .env file or a terminal `$env:` assignment makes the Authorization
# header itself invalid (`Bearer sk-...\n`), which surfaces as an opaque
# httpcore "Illegal header value" / connection error, not an auth error --
# very easy to mistake for a code bug.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()