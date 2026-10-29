"""
Consultas ao alerta de surtos, gravado todo mês pelo job
epidemiological-ds-alert (data_science/src/epidemiological_intelligence/alert):

- BigQuery `outbreak_alerts`: uma linha por rodada × origem × série ×
  horizonte; aqui sempre só a rodada mais recente (MAX(run_id));
- GCS `<prefixo>/latest.json`: modelo, cortes, métricas do teste e as
  origens da rodada.

Duas origens por doença: "fechado" (último mês com dados completos) e
"provisorio" (último mês disponível, com dados ainda incompletos).
"""

import json
import time
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
from google.cloud import bigquery, storage

from epidemiological_agent.config import (
    ALERT_ARTIFACT_PREFIX,
    ARTIFACT_BUCKET,
    BIGQUERY_ALERT_TABLE,
    BIGQUERY_DATASET,
    PROJECT_ID,
)
from epidemiological_agent.tools.gold_queries import DIM_TABLE, run_query

ALERT_TABLE = f"`{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_ALERT_TABLE}`"
LATEST_RUN = f"run_id = (SELECT MAX(run_id) FROM {ALERT_TABLE})"

LEVELS = ("uf", "municipio")
ORIGIN_TYPES = ("fechado", "provisorio")
MAX_ROWS = 5000

_MODEL_TTL_SECONDS = 300
_model_cache: dict[str, tuple[float, dict | None]] = {}


@dataclass(frozen=True)
class AlertFilters:
    level: str = "uf"
    origin_type: str = "fechado"
    disease: str | None = None
    state: str | None = None
    municipality_code: str | None = None
    horizon: int | None = None
    only_alerts: bool = False


def _where(filters: AlertFilters) -> tuple[str, list]:
    conditions = [LATEST_RUN, "a.level = @level", "a.origin_type = @origin_type"]
    parameters = [
        bigquery.ScalarQueryParameter("level", "STRING", filters.level),
        bigquery.ScalarQueryParameter("origin_type", "STRING", filters.origin_type),
    ]
    if filters.disease:
        conditions.append("UPPER(a.disease) = @disease")
        parameters.append(bigquery.ScalarQueryParameter("disease", "STRING", filters.disease.upper()))
    if filters.state:
        conditions.append("a.state = @state")
        parameters.append(bigquery.ScalarQueryParameter("state", "STRING", filters.state.upper()))
    if filters.municipality_code:
        conditions.append("a.municipality_code = @municipality_code")
        parameters.append(bigquery.ScalarQueryParameter("municipality_code", "STRING", filters.municipality_code))
    if filters.horizon:
        conditions.append("a.horizon = @horizon")
        parameters.append(bigquery.ScalarQueryParameter("horizon", "INT64", filters.horizon))
    if filters.only_alerts:
        conditions.append("a.alert")
    return " AND ".join(conditions), parameters


def latest_alerts(filters: AlertFilters, limit: int = 500) -> pd.DataFrame:
    """Linhas da rodada mais recente, maior probabilidade primeiro (com o nome do município)."""

    where, parameters = _where(filters)
    parameters.append(bigquery.ScalarQueryParameter("limit", "INT64", min(limit, MAX_ROWS)))
    sql = f"""
        SELECT
            a.run_id, a.model_version, a.origin_type, a.origin_month, a.level, a.disease, a.source,
            a.state, a.municipality_code, d.municipality_name, a.target_month, a.horizon,
            a.threshold, a.cases_p10, a.cases_p50, a.cases_p90, a.probability, a.cutoff, a.alert,
            a.observed_cases, a.target_provisional
        FROM {ALERT_TABLE} AS a
        LEFT JOIN {DIM_TABLE} AS d ON d.municipality_code_6 = a.municipality_code
        WHERE {where}
        ORDER BY a.probability DESC, a.disease, a.state, a.horizon
        LIMIT @limit
    """
    return run_query(sql, parameters)


def state_summary(origin_type: str, horizon: int, disease: str | None = None) -> pd.DataFrame:
    """
    Por UF, para o mapa: maior probabilidade de surto da UF entre as
    doenças (ou da doença dada), quantas doenças estão em alerta na UF e
    quantos municípios × doença estão em alerta.
    """

    conditions = [LATEST_RUN, "origin_type = @origin_type", "horizon = @horizon"]
    parameters = [
        bigquery.ScalarQueryParameter("origin_type", "STRING", origin_type),
        bigquery.ScalarQueryParameter("horizon", "INT64", horizon),
    ]
    if disease:
        conditions.append("UPPER(disease) = @disease")
        parameters.append(bigquery.ScalarQueryParameter("disease", "STRING", disease.upper()))
    sql = f"""
        SELECT
            state,
            MAX(IF(level = 'uf', probability, NULL)) AS max_probability,
            COUNTIF(level = 'uf' AND alert) AS state_alerts,
            COUNTIF(level = 'municipio' AND alert) AS municipality_alerts
        FROM {ALERT_TABLE}
        WHERE {" AND ".join(conditions)}
        GROUP BY state
        ORDER BY state
    """
    return run_query(sql, parameters)


def alerts_by_disease(origin_type: str = "fechado") -> pd.DataFrame:
    """disease, state_alerts (UFs em alerta em algum horizonte), max_probability (da UF)."""

    sql = f"""
        SELECT
            disease,
            COUNT(DISTINCT IF(alert, state, NULL)) AS state_alerts,
            MAX(probability) AS max_probability
        FROM {ALERT_TABLE}
        WHERE {LATEST_RUN} AND level = 'uf' AND origin_type = @origin_type
        GROUP BY disease
    """
    return run_query(sql, [bigquery.ScalarQueryParameter("origin_type", "STRING", origin_type)])


@lru_cache(maxsize=1)
def _get_storage_client() -> storage.Client:
    return storage.Client(project=PROJECT_ID)


def model_info() -> dict | None:
    """latest.json da última rodada (modelo, cortes, métricas, origens); None se o job nunca rodou."""

    cached = _model_cache.get("latest")
    if cached is not None and time.time() - cached[0] < _MODEL_TTL_SECONDS:
        return cached[1]

    blob = _get_storage_client().bucket(ARTIFACT_BUCKET).blob(f"{ALERT_ARTIFACT_PREFIX.rstrip('/')}/latest.json")
    info = json.loads(blob.download_as_text(encoding="utf-8")) if blob.exists() else None
    _model_cache["latest"] = (time.time(), info)
    return info
