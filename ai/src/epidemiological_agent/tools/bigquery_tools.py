"""
Consultas ao gold usadas pela rota /data e pelas ferramentas do chat.

Os filtros (doença, UF, município por código ou por nome, período)
são os mesmos de tools/gold_queries.py. Sem município, os registros
vêm agregados por mês -- o gold nacional tem ~10 milhões de linhas e
não cabe numa resposta.
"""

import pandas as pd

from epidemiological_agent.tools.gold_queries import (
    GOLD_TABLE,
    STATE_NAMES,
    GoldFilters,
    run_query,
    where_clause,
)

CLIMATE_COLUMNS = [
    "precipitation_sum_mm",
    "precipitation_max_observation_mm",
    "temperature_avg_c",
    "dew_point_avg_c",
    "relative_humidity_avg_pct",
    "atmospheric_pressure_avg_mb",
    "wind_speed_avg_ms",
    "wind_gust_max_ms",
]

# Mantido para quem importava o nome antigo.
_CLIMATE_COLUMNS = CLIMATE_COLUMNS


def _filters(disease, municipality, start_date, end_date, state, municipality_code) -> GoldFilters:
    return GoldFilters(
        diseases=(disease,) if disease else (),
        state=state,
        municipality_code=municipality_code,
        municipality=municipality,
        start_date=start_date,
        end_date=end_date,
    )


def get_max_reference_date() -> pd.Timestamp | None:
    """
    Most recent reference_date present in the Gold table.

    Used to tell apart a request for a period the project genuinely
    has no data for from an ordinary empty filter combination.
    """

    df = run_query(f"SELECT MAX(reference_date) AS max_date FROM {GOLD_TABLE}", [])
    max_date = df["max_date"].iloc[0] if not df.empty else None

    if max_date is None or pd.isna(max_date):
        return None

    return pd.Timestamp(max_date).tz_localize(None) if pd.Timestamp(max_date).tzinfo else pd.Timestamp(max_date)


def query_epidemiological_data(
    disease: str | None = None,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    state: str | None = None,
    municipality_code: str | None = None,
) -> pd.DataFrame:
    """
    Registros mensais de casos e clima.

    - Com município (código ou nome): uma linha por município × mês ×
      doença. Um nome sem UF pode trazer homônimos de UFs diferentes;
      as colunas state/municipality_code permitem distinguir.
    - Sem município: casos somados e clima médio por mês × doença, na
      UF filtrada ou no Brasil.
    """

    filters = _filters(disease, municipality, start_date, end_date, state, municipality_code)
    where, parameters = where_clause(filters)
    climate = ", ".join(CLIMATE_COLUMNS)

    if municipality or municipality_code:
        sql = f"""
            SELECT
                reference_date, disease, municipality_name AS municipality,
                state, municipality_code, cases, {climate}
            FROM {GOLD_TABLE}
            WHERE {where}
            ORDER BY state, municipality_code, reference_date
        """
    else:
        label = STATE_NAMES.get((state or "").upper(), "BRASIL") if state else "BRASIL"
        averages = ", ".join(f"AVG({column}) AS {column}" for column in CLIMATE_COLUMNS)
        sql = f"""
            SELECT
                reference_date, disease, '{label}' AS municipality,
                {"@state" if state else "CAST(NULL AS STRING)"} AS state,
                CAST(NULL AS STRING) AS municipality_code,
                SUM(cases) AS cases, {averages}
            FROM {GOLD_TABLE}
            WHERE {where}
            GROUP BY reference_date, disease
            ORDER BY disease, reference_date
        """

    df = run_query(sql, parameters)
    if "reference_date" in df.columns:
        df["reference_date"] = pd.to_datetime(df["reference_date"], utc=True).dt.tz_localize(None)
    return df


def get_total_cases(
    disease: str | None,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    state: str | None = None,
    municipality_code: str | None = None,
) -> int:
    where, parameters = where_clause(
        _filters(disease, municipality, start_date, end_date, state, municipality_code)
    )
    df = run_query(f"SELECT SUM(cases) AS total_cases FROM {GOLD_TABLE} WHERE {where}", parameters)

    total = df["total_cases"].iloc[0] if not df.empty else None
    return int(total) if total is not None and not pd.isna(total) else 0


def get_climate_summary(
    disease: str | None = None,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    state: str | None = None,
    municipality_code: str | None = None,
) -> dict:
    """
    Aggregated (avg/min/max) climate stats over the matching rows.

    Climate repeats once per disease for the same municipality/month,
    so the CTE collapses back to one row per municipality/month before
    aggregating -- otherwise each reading would count once per disease.
    """

    where, parameters = where_clause(
        _filters(disease, municipality, start_date, end_date, state, municipality_code)
    )
    select_clause = ",\n            ".join(
        f"AVG({column}) AS {column}_avg, MIN({column}) AS {column}_min, MAX({column}) AS {column}_max"
        for column in CLIMATE_COLUMNS
    )
    sql = f"""
        WITH climate_rows AS (
            SELECT DISTINCT municipality_code, reference_date, {", ".join(CLIMATE_COLUMNS)}
            FROM {GOLD_TABLE}
            WHERE {where}
        )
        SELECT
            {select_clause}
        FROM climate_rows
    """
    row = run_query(sql, parameters).iloc[0]

    def _none_or_float(value):
        return None if value is None or pd.isna(value) else float(value)

    return {
        column: {
            "avg": _none_or_float(row[f"{column}_avg"]),
            "min": _none_or_float(row[f"{column}_min"]),
            "max": _none_or_float(row[f"{column}_max"]),
        }
        for column in CLIMATE_COLUMNS
    }
