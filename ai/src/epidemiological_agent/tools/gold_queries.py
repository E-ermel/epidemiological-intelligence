"""
Consultas agregadas ao gold nacional no BigQuery.

O gold tem ~10 milhões de linhas (5.571 municípios × ~140 meses × 13
doenças): nada aqui carrega a tabela inteira. Cada função devolve só o
agregado que uma rota precisa, e o resultado fica em cache por alguns
minutos -- o gold só muda quando o pipeline de DE roda.

Municípios são identificados pelo código de 6 dígitos (DATASUS), não
pelo nome: há homônimos em UFs diferentes (Santa Maria/RS e /RN).
"""

import time
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
from google.cloud import bigquery

from epidemiological_agent.config import (
    BIGQUERY_DATASET,
    BIGQUERY_DIM_MUNICIPALITY_TABLE,
    BIGQUERY_TABLE,
    PROJECT_ID,
)


@lru_cache(maxsize=1)
def get_bigquery_client() -> bigquery.Client:
    # Constructing a client does credential discovery on every call;
    # bigquery.Client is documented safe to reuse across queries.
    return bigquery.Client(project=PROJECT_ID)


GOLD_TABLE = f"`{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}`"
DIM_TABLE = f"`{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_DIM_MUNICIPALITY_TABLE}`"

_CACHE_TTL_SECONDS = 300
_cache: dict[tuple, tuple[float, pd.DataFrame]] = {}

STATE_NAMES: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}


def normalize_name(name: str) -> str:
    """Mesmo formato da coluna `municipality` do gold: maiúsculas, sem acento."""

    without_accents = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(without_accents.upper().split())


@dataclass(frozen=True)
class GoldFilters:
    diseases: tuple[str, ...] = ()
    state: str | None = None
    municipality_code: str | None = None
    municipality: str | None = None
    start_date: str | None = None
    end_date: str | None = None


def where_clause(filters: GoldFilters, alias: str = "") -> tuple[str, list]:
    """WHERE parametrizado para os filtros dados (nunca interpola valores no SQL)."""

    prefix = f"{alias}." if alias else ""
    conditions, parameters = ["TRUE"], []

    if filters.diseases:
        conditions.append(f"UPPER({prefix}disease) IN UNNEST(@diseases)")
        parameters.append(bigquery.ArrayQueryParameter("diseases", "STRING", [d.upper() for d in filters.diseases]))

    if filters.state:
        conditions.append(f"{prefix}state = @state")
        parameters.append(bigquery.ScalarQueryParameter("state", "STRING", filters.state.upper()))

    if filters.municipality_code:
        conditions.append(f"{prefix}municipality_code = @municipality_code")
        parameters.append(bigquery.ScalarQueryParameter("municipality_code", "STRING", filters.municipality_code))

    if filters.municipality:
        conditions.append(f"{prefix}municipality = @municipality")
        parameters.append(bigquery.ScalarQueryParameter("municipality", "STRING", normalize_name(filters.municipality)))

    if filters.start_date:
        conditions.append(f"{prefix}reference_date >= @start_date")
        parameters.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", filters.start_date))

    if filters.end_date:
        conditions.append(f"{prefix}reference_date <= @end_date")
        parameters.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", filters.end_date))

    return " AND ".join(conditions), parameters


def run_query(sql: str, parameters: list) -> pd.DataFrame:
    """Executa com cache curto, chaveado pelo SQL e pelos valores dos parâmetros."""

    key = (sql, tuple((p.name, str(getattr(p, "value", getattr(p, "values", None)))) for p in parameters))
    cached = _cache.get(key)
    if cached is not None and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1].copy()

    job_config = bigquery.QueryJobConfig(query_parameters=parameters)
    df = get_bigquery_client().query(sql, job_config=job_config).to_dataframe()

    _cache[key] = (time.time(), df)
    return df.copy()


def _normalize_dates(df: pd.DataFrame, column: str = "reference_date") -> pd.DataFrame:
    # TIMESTAMP vem com fuso (UTC); os filtros do frontend chegam sem.
    if column in df.columns:
        df[column] = pd.to_datetime(df[column], utc=True).dt.tz_localize(None)
    return df


# ---------------------------------------------------------------------
# Agregados
# ---------------------------------------------------------------------


def monthly_cases(filters: GoldFilters) -> pd.DataFrame:
    """reference_date, cases: soma por mês."""

    where, parameters = where_clause(filters)
    sql = f"""
        SELECT reference_date, SUM(cases) AS cases
        FROM {GOLD_TABLE}
        WHERE {where}
        GROUP BY reference_date
        ORDER BY reference_date
    """
    return _normalize_dates(run_query(sql, parameters))


def cases_by_disease(filters: GoldFilters) -> pd.DataFrame:
    """disease, cases, municipality_count (municípios com ao menos um caso)."""

    where, parameters = where_clause(filters)
    sql = f"""
        SELECT
            disease,
            SUM(cases) AS cases,
            COUNT(DISTINCT IF(cases > 0, municipality_code, NULL)) AS municipality_count
        FROM {GOLD_TABLE}
        WHERE {where}
        GROUP BY disease
        ORDER BY disease
    """
    return run_query(sql, parameters)


def municipality_count(filters: GoldFilters) -> int:
    """Municípios com ao menos um caso no filtro."""

    where, parameters = where_clause(filters)
    sql = f"""
        SELECT COUNT(DISTINCT IF(cases > 0, municipality_code, NULL)) AS n
        FROM {GOLD_TABLE}
        WHERE {where}
    """
    df = run_query(sql, parameters)
    return int(df["n"].iloc[0]) if not df.empty else 0


def cases_by_state(filters: GoldFilters) -> pd.DataFrame:
    """state, cases."""

    where, parameters = where_clause(filters)
    sql = f"""
        SELECT state, SUM(cases) AS cases
        FROM {GOLD_TABLE}
        WHERE {where}
        GROUP BY state
    """
    return run_query(sql, parameters)


def cases_by_municipality(filters: GoldFilters) -> pd.DataFrame:
    """municipality_code, municipality_name, state, latitude, longitude, cases."""

    where, parameters = where_clause(filters, alias="g")
    sql = f"""
        SELECT
            g.municipality_code,
            ANY_VALUE(g.municipality_name) AS municipality_name,
            ANY_VALUE(g.state) AS state,
            ANY_VALUE(d.latitude) AS latitude,
            ANY_VALUE(d.longitude) AS longitude,
            SUM(g.cases) AS cases
        FROM {GOLD_TABLE} AS g
        LEFT JOIN {DIM_TABLE} AS d ON d.municipality_code_6 = g.municipality_code
        WHERE {where}
        GROUP BY g.municipality_code
    """
    return run_query(sql, parameters)


def diseases() -> list[str]:
    df = run_query(f"SELECT DISTINCT disease FROM {GOLD_TABLE} ORDER BY disease", [])
    return df["disease"].tolist()


def municipalities(state: str | None = None) -> pd.DataFrame:
    """municipality_code (6 dígitos), municipality_name, state -- da dim do IBGE."""

    conditions, parameters = "TRUE", []
    if state:
        conditions = "state = @state"
        parameters.append(bigquery.ScalarQueryParameter("state", "STRING", state.upper()))

    sql = f"""
        SELECT municipality_code_6 AS municipality_code, municipality_name, state
        FROM {DIM_TABLE}
        WHERE {conditions}
        ORDER BY state, municipality_name
    """
    return run_query(sql, parameters)
