"""
Publicação do alerta:

- BigQuery `outbreak_alerts`: uma linha por rodada × origem × série ×
  horizonte (append; a API lê a rodada mais recente, run_id);
- GCS `<prefixo>/latest.json`: modelo, cortes, métricas do teste e o
  resumo da rodada.

Localmente (ALERT_OUTPUT_DIR) grava alerts.parquet e latest.json numa pasta.
"""

import json
from pathlib import Path

import pandas as pd

from epidemiological_intelligence.alert import config

ALERT_COLUMNS = [
    "run_id", "model_version", "origin_type", "origin_month", "level", "disease", "source", "state",
    "municipality_code", "target_month", "horizon", "threshold", "cases_p10", "cases_p50", "cases_p90",
    "probability", "cutoff", "alert", "observed_cases", "target_provisional",
]


def summary(alerts: pd.DataFrame, run_id: pd.Timestamp) -> dict:
    origins = alerts.groupby(["origin_type", "disease"])["origin_month"].first().reset_index()
    counts = alerts[alerts["alert"]].groupby(["origin_type", "level", "horizon"]).size()
    return {
        "run_id": run_id.isoformat(),
        "model_version": config.MODEL_VERSION,
        "model": {
            "name": "Chronos-2 (Amazon), zero-shot",
            "covariates": config.CLIMATE,
            "cross_learning_batch": config.CROSS_LEARNING_BATCH,
            "horizons": config.HORIZONS,
        },
        "outbreak_definition": {
            "channel_years": config.CHANNEL_YEARS,
            "channel_z": config.CHANNEL_Z,
            "min_cases": config.MIN_CASES,
            "min_mean_cases_municipio": config.MIN_MEAN_CASES_MUNICIPIO,
        },
        "cutoffs": config.CUTOFFS,
        "test_metrics": config.TEST_METRICS,
        "origins": [
            {"origin_type": r.origin_type, "disease": r.disease, "origin_month": r.origin_month.date().isoformat()}
            for r in origins.itertuples()
        ],
        "alerts": [
            {"origin_type": t, "level": lv, "horizon": int(h), "count": int(n)} for (t, lv, h), n in counts.items()
        ],
        "rows": int(len(alerts)),
    }


def to_local(alerts: pd.DataFrame, meta: dict, output_dir: str) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    alerts[ALERT_COLUMNS].to_parquet(path / "alerts.parquet", index=False)
    (path / "latest.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def to_cloud(alerts: pd.DataFrame, meta: dict) -> None:
    from google.cloud import bigquery, storage

    table = f"{config.GCP_PROJECT_ID}.{config.BIGQUERY_DATASET}.{config.BIGQUERY_ALERT_TABLE}"
    df = alerts[ALERT_COLUMNS].copy()
    for column in ("origin_month", "target_month"):
        df[column] = pd.to_datetime(df[column]).dt.date
    job = bigquery.Client(project=config.GCP_PROJECT_ID).load_table_from_dataframe(
        df,
        table,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            time_partitioning=bigquery.TimePartitioning(field="run_id"),
            schema=[
                bigquery.SchemaField("run_id", "TIMESTAMP"),
                bigquery.SchemaField("origin_month", "DATE"),
                bigquery.SchemaField("target_month", "DATE"),
                bigquery.SchemaField("municipality_code", "STRING"),
                bigquery.SchemaField("target_provisional", "BOOLEAN"),
            ],
        ),
    )
    job.result()

    blob = storage.Client(project=config.GCP_PROJECT_ID).bucket(config.ARTIFACT_BUCKET).blob(
        f"{config.ALERT_ARTIFACT_PREFIX}/latest.json"
    )
    blob.upload_from_string(json.dumps(meta, indent=2, ensure_ascii=False), content_type="application/json")
