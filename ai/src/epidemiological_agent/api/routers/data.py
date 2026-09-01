import pandas as pd
from fastapi import APIRouter, Query

from epidemiological_agent.api.gold_data import load_gold_dataframe
from epidemiological_agent.api.schemas_data import EpidemiologicalRecord
from epidemiological_agent.tools.bigquery_tools import query_epidemiological_data

router = APIRouter(tags=["data"])

_CLIMATE_COLUMNS = [
    "precipitation_sum_mm",
    "precipitation_max_observation_mm",
    "temperature_avg_c",
    "dew_point_avg_c",
    "relative_humidity_avg_pct",
    "atmospheric_pressure_avg_mb",
    "wind_speed_avg_ms",
    "wind_gust_max_ms",
]


def _none_if_nan(value) -> float | None:
    # pd.isna() covers None, float NaN, and pandas' own NA marker
    # (pd.NA -- what a nullable-dtype column, e.g. an Int64/Float64
    # "cases" column with a missing LEFT JOIN match, actually holds).
    # math.isnan(pd.NA) raises TypeError, and the old except branch
    # returned pd.NA unchanged, which Pydantic then rejected as
    # "not a valid float" -- a 500 on any row with a missing value.
    if pd.isna(value):
        return None
    return float(value)


@router.get("/data", response_model=list[EpidemiologicalRecord])
def get_data(
    disease: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> list[EpidemiologicalRecord]:
    """
    Thin wrapper around query_epidemiological_data() -- the same 4
    filters the Explorar Dados page's (currently disabled) filter bar
    already draws.
    """

    df = query_epidemiological_data(
        disease=disease,
        municipality=municipality,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        EpidemiologicalRecord(
            reference_date=pd.Timestamp(row.reference_date).date().isoformat(),
            disease=row.disease,
            municipality=row.municipality,
            cases=_none_if_nan(row.cases),
            **{
                column: _none_if_nan(getattr(row, column))
                for column in _CLIMATE_COLUMNS
            },
        )
        for row in df.itertuples()
    ]


@router.get("/municipalities", response_model=list[str])
def get_municipalities() -> list[str]:
    """
    Distinct municipalities in the Gold table -- backs the municipality
    <select> in Explorar Dados and the per-study dashboard, both of
    which used to be a free-text field with no real list behind it.
    Uses the cached full table (load_gold_dataframe) rather than a
    fresh BigQuery query, same reasoning as /overview and /studies.
    """

    df = load_gold_dataframe()
    return sorted(df["municipality"].dropna().unique().tolist())
