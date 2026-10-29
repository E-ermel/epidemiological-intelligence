from epidemiological_agent.api.schemas_base import CamelModel


class EpidemiologicalRecord(CamelModel):
    """
    Mirrors the SELECT columns of query_epidemiological_data() in
    tools/bigquery_tools.py. Climate fields are nullable: absence of
    climate data must never drop the epidemiological record.

    `municipality` is the municipality name, or the state/"BRASIL"
    label when the records are aggregated (no municipality filter) --
    then `municipality_code` is null.
    """

    reference_date: str
    disease: str
    municipality: str
    state: str | None = None
    municipality_code: str | None = None
    cases: float | None
    precipitation_sum_mm: float | None
    precipitation_max_observation_mm: float | None
    temperature_avg_c: float | None
    dew_point_avg_c: float | None
    relative_humidity_avg_pct: float | None
    atmospheric_pressure_avg_mb: float | None
    wind_speed_avg_ms: float | None
    wind_gust_max_ms: float | None
