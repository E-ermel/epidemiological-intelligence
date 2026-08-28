import math

import pandas as pd
from fastapi import APIRouter, Query

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
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except TypeError:
        return value
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
