import re
from typing import Dict, List, Optional

import pandas as pd

from epidemiological_de.inmet.extract import DATA_LINE_PATTERN


NUMERIC_COLUMNS = [
    "precipitation_mm",
    "atmospheric_pressure_mb",
    "temperature_c",
    "dew_point_temperature_c",
    "relative_humidity_pct",
    "wind_direction_deg",
    "wind_gust_ms",
    "wind_speed_ms",
]

FIELD_INDICES = {
    "date": 0,
    "hour": 1,
    "precipitation_mm": 2,
    "atmospheric_pressure_mb": 3,
    "temperature_c": 7,
    "dew_point_temperature_c": 8,
    "relative_humidity_pct": 15,
    "wind_direction_deg": 16,
    "wind_gust_ms": 17,
    "wind_speed_ms": 18,
}

# INMET_<região>_<UF>_<código>_<nome>_<dd-mm-aaaa>... (qualquer UF; antes
# o padrão só aceitava S_RS, da época em que o bronze era só do RS).
MUNICIPALITY_FROM_FILE_PATTERN = re.compile(
    r"INMET_[A-Z]{1,2}_[A-Z]{2}_[A-Z0-9]+_(.*?)_\d{2}-\d{2}-\d{4}"
)
HOUR_UTC_SUFFIX_PATTERN = re.compile(r"\s*UTC$")
HOUR_HHMM_PATTERN = re.compile(r"^\d{4}$")


def _split_fields(line: str) -> List[Optional[str]]:
    fields = line.split(";")

    max_index = max(FIELD_INDICES.values())
    if len(fields) <= max_index:
        fields = fields + [None] * (max_index + 1 - len(fields))

    return fields


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def build_silver_dataframe(
    lines: List[str],
    metadata: Dict[str, str],
    file_path: str,
) -> pd.DataFrame:

    data_lines = [line for line in lines if DATA_LINE_PATTERN.match(line)]

    records = []
    for line in data_lines:
        fields = _split_fields(line)
        records.append(
            {name: fields[index] for name, index in FIELD_INDICES.items()}
        )

    df = pd.DataFrame(records, columns=list(FIELD_INDICES.keys()))

    for column in NUMERIC_COLUMNS:
        cleaned = (
            df[column]
            .astype("string")
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        cleaned = cleaned.mask(cleaned.isin(["-9999", ""]))
        # Float64 fixo: o try_cast do Spark sempre produz double, enquanto o
        # to_numeric inferiria Int64 em arquivos sem casas decimais.
        df[column] = pd.to_numeric(cleaned, errors="coerce").astype("Float64")

    df["date"] = df["date"].astype("string").str.replace("/", "-", regex=False)

    hour = df["hour"].astype("string").str.strip()
    hour = hour.str.replace(HOUR_UTC_SUFFIX_PATTERN, "", regex=True)
    is_hhmm = hour.str.match(HOUR_HHMM_PATTERN).fillna(False)
    hour = hour.where(~is_hhmm, hour.str[:2] + ":" + hour.str[2:])
    df["hour"] = hour

    df["timestamp"] = pd.to_datetime(
        df["date"] + " " + df["hour"],
        format="%Y-%m-%d %H:%M",
        errors="coerce",
    )
    df = df.drop(columns=["date", "hour"])

    station_name = metadata.get("station_name")

    df["station_code"] = metadata.get("station_code")
    df["station_name"] = station_name
    df["municipality"] = (
        station_name.strip().upper() if station_name is not None else None
    )
    df["state"] = metadata.get("state")
    df["latitude"] = _to_float(metadata.get("latitude"))
    df["longitude"] = _to_float(metadata.get("longitude"))
    df["altitude"] = _to_float(metadata.get("altitude"))
    df["source_file"] = file_path
    df["ingestion_timestamp"] = pd.Timestamp.now(tz="UTC")

    return df


def standardize_inmet_silver(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    municipality_from_file = (
        df["source_file"]
        .astype("string")
        .str.extract(MUNICIPALITY_FROM_FILE_PATTERN, expand=False)
    )
    fallback_municipality = municipality_from_file.str.strip().str.upper()

    # Em alguns arquivos (especialmente 2019), o nome da estação não foi
    # recuperado do cabeçalho. O nome do arquivo é usado como fallback.
    df["municipality"] = df["municipality"].where(
        df["municipality"].notna(), fallback_municipality
    )

    df["station_name"] = df["station_name"].where(
        df["station_name"].notna(), df["municipality"]
    )

    df["year"] = df["timestamp"].dt.year

    return df


def aggregate_station_monthly(inmet_df: pd.DataFrame) -> pd.DataFrame:
    """
    Horário -> estação × mês. Feito no pipeline do INMET, ano a ano,
    para o gold não precisar carregar o silver horário do Brasil todo
    (~5 milhões de linhas por ano).
    """

    inmet_df = inmet_df.copy()
    inmet_df["year"] = inmet_df["timestamp"].dt.year
    inmet_df["month"] = inmet_df["timestamp"].dt.month

    # dropna=False mantém timestamps inválidos como grupo próprio, como o
    # groupBy do Spark do notebook original.
    return inmet_df.groupby(
        ["station_code", "year", "month"],
        as_index=False,
        dropna=False,
    ).agg(
        precipitation_sum_mm=("precipitation_mm", lambda s: s.sum(min_count=1)),
        precipitation_avg_observation_mm=("precipitation_mm", "mean"),
        precipitation_max_observation_mm=("precipitation_mm", "max"),
        temperature_avg_c=("temperature_c", "mean"),
        dew_point_avg_c=("dew_point_temperature_c", "mean"),
        relative_humidity_avg_pct=("relative_humidity_pct", "mean"),
        atmospheric_pressure_avg_mb=("atmospheric_pressure_mb", "mean"),
        wind_speed_avg_ms=("wind_speed_ms", "mean"),
        wind_gust_max_ms=("wind_gust_ms", "max"),
    )
