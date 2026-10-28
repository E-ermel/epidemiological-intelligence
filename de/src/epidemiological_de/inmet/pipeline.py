import json
import re
import zipfile

import fsspec
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from epidemiological_de import config, ingestion, storage
from epidemiological_de.ibge.ingest import MALHA_FILE
from epidemiological_de.inmet import extract, transform
from epidemiological_de.inmet import stations as station_mapping

STATION_METADATA_COLUMNS = ["station_code", "station_name", "state", "latitude", "longitude"]

YEAR_DIR_PATTERN = re.compile(r"year=(\d{4})")

# INMET_CO_DF_A001_BRASILIA_01-01-2026_A_30-09-2026.CSV
MEMBER_PATTERN = re.compile(
    r"INMET_[A-Z]{1,2}_[A-Z]{2}_([A-Z0-9]+)_.*_\d{2}-\d{2}-\d{4}_A_(\d{2})-(\d{2})-(\d{4})\.CSV$",
    re.IGNORECASE,
)


def latest_station_members(names: list[str]) -> list[str]:
    """
    Um CSV por estação: o de data final mais recente. O zip do ano
    corrente pode trazer a versão antiga ao lado da nova (o de 2026 veio
    com "..._A_31-08-2026" e "..._A_30-09-2026" de cada estação); ler as
    duas duplicaria cada hora. Nomes fora do padrão passam como estão.
    """

    latest: dict[str, tuple[tuple[int, int, int], str]] = {}
    others = []

    for name in names:
        match = MEMBER_PATTERN.search(name.split("/")[-1])
        if match is None:
            others.append(name)
            continue

        station, day, month, year = match.groups()
        end = (int(year), int(month), int(day))
        if station not in latest or end > latest[station][0]:
            latest[station] = (end, name)

    return sorted(others + [name for _, name in latest.values()])


def parse_inmet_file(file_path: str) -> pd.DataFrame:
    lines = extract.read_raw_lines(file_path)
    metadata = extract.extract_metadata(lines)
    return transform.build_silver_dataframe(lines, metadata, file_path)


def parse_inmet_lines(lines: list[str], source_file: str) -> pd.DataFrame:
    metadata = extract.extract_metadata(lines)
    df = transform.build_silver_dataframe(lines, metadata, source_file)
    return transform.standardize_inmet_silver(df)


def build_inmet_silver(files: list) -> pd.DataFrame:
    all_dfs = [parse_inmet_file(file_path) for file_path in files]

    if not all_dfs:
        raise ValueError("Nenhum arquivo CSV do INMET foi encontrado.")

    print("DataFrames processados:", len(all_dfs))

    inmet_silver_df = pd.concat(all_dfs, ignore_index=True, sort=False)
    return transform.standardize_inmet_silver(inmet_silver_df)


def list_year_zips(root: str | None = None) -> list[tuple[int, str]]:
    """Zips ingeridos por inmet/ingest.py: bronze/inmet/year=AAAA/AAAA.zip."""

    root = (root or config.BRONZE_ROOT).rstrip("/")
    fs, base = fsspec.core.url_to_fs(f"{root}/{config.INMET_SOURCE}")
    protocol = fs.protocol[0] if isinstance(fs.protocol, (list, tuple)) else fs.protocol
    prefix = "" if protocol == "file" else f"{protocol}://"

    found = []
    for path in fs.glob(f"{base}/year=*/*.zip"):
        match = YEAR_DIR_PATTERN.search(path)
        if match:
            found.append((int(match.group(1)), f"{prefix}{path}"))

    return sorted(found)


def process_year(zip_path: str, year: int, silver_root: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Lê o zip de um ano estação a estação e grava o silver horário em
    <silver_root>/year=AAAA/part-0.parquet de forma incremental
    (ParquetWriter). Juntar o ano inteiro num DataFrame -- ~565
    estações, ~5 milhões de linhas -- não cabe nos 4 GiB do job.

    Devolve o agregado estação × mês e os metadados de cada estação.
    """

    year_dir = f"{silver_root.rstrip('/')}/year={year}"
    storage.clear_path(year_dir)
    dest = f"{year_dir}/part-0.parquet"

    monthly, stations = [], []
    written_rows = null_timestamps = duplicates = 0
    writer, schema = None, None

    with fsspec.open(zip_path, "rb") as raw, zipfile.ZipFile(raw) as archive, \
            fsspec.open(dest, "wb", auto_mkdir=True) as out:

        members = latest_station_members([name for name in archive.namelist() if name.lower().endswith(".csv")])

        for member in members:
            lines = re.split(r"\r?\n", archive.read(member).decode("ISO-8859-1"))
            df = parse_inmet_lines(lines, f"{zip_path}::{member}")
            if df.empty:
                continue

            null_timestamps += int(df["timestamp"].isna().sum())
            duplicates += int(df.duplicated(["station_code", "timestamp"]).sum())

            monthly.append(transform.aggregate_station_monthly(df))
            stations.append(df[STATION_METADATA_COLUMNS].iloc[[0]])

            # `year` fica no caminho (partição hive), não no arquivo.
            table = pa.Table.from_pandas(df.drop(columns=["year"]), preserve_index=False)
            if writer is None:
                schema = table.schema
                writer = pq.ParquetWriter(out, schema)
            else:
                # Estação com coluna toda nula vira tipo `null` no Arrow;
                # o cast alinha com o schema do primeiro arquivo.
                table = table.cast(schema)

            writer.write_table(table)
            written_rows += table.num_rows

        if writer is not None:
            writer.close()

    with fsspec.open(dest, "rb") as f:
        stored_rows = pq.ParquetFile(f).metadata.num_rows
    print(
        f"{year}: {len(members)} estações, {written_rows} registros, "
        f"timestamps nulos={null_timestamps}, duplicatas estação+timestamp={duplicates}"
    )
    if stored_rows != written_rows:
        raise ValueError(f"{year}: contagem divergente, escrito={written_rows}, lido={stored_rows}")

    station_monthly = pd.concat(monthly, ignore_index=True) if monthly else pd.DataFrame()
    station_monthly = station_monthly.dropna(subset=["year", "month"]).astype({"year": "int64", "month": "int64"})

    return station_monthly, pd.concat(stations, ignore_index=True).assign(source_year=year)


def _read_latest_mesh(root: str | None = None) -> dict:
    path = ingestion.latest_file(config.IBGE_SOURCE, MALHA_FILE, root)
    if path is None:
        raise FileNotFoundError(
            f"{MALHA_FILE} não encontrado no bronze do IBGE -- rode antes "
            f"`python -m epidemiological_de.ibge.ingest`."
        )

    with fsspec.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_station_report(station_map: pd.DataFrame) -> None:
    print("Estações:", len(station_map))
    print("Método de associação:", station_map["match_method"].value_counts(dropna=False).to_dict())

    unmatched = station_map["municipality_code"].isna().sum()
    print("Sem município:", unmatched)

    # Só as associações que não vieram do nome: distância grande pelo
    # nome é normal em municípios enormes (Altamira/PA tem ~160 mil km²).
    far = station_map[(station_map["match_method"] != "name") & (station_map["distance_km"] > 50)]
    if not far.empty:
        print("Associações por polígono/proximidade a mais de 50 km do centróide (revisar):")
        print(far[["station_code", "station_name", "state", "municipality_name", "match_method", "distance_km"]].to_string())


def run_pipeline(root: str | None = None) -> None:
    zips = list_year_zips(root)
    if not zips:
        raise ValueError(
            "Nenhum zip do INMET no bronze -- rode antes "
            "`python -m epidemiological_de.inmet.ingest`."
        )

    print("Anos encontrados:", [year for year, _ in zips])

    monthly, stations = [], []
    for year, path in zips:
        station_monthly, station_metadata = process_year(path, year, config.INMET_SILVER_PATH)
        monthly.append(station_monthly)
        stations.append(station_metadata)

    station_monthly = pd.concat(monthly, ignore_index=True)
    storage.clear_path(config.INMET_STATION_MONTHLY_SILVER_PATH)
    station_monthly.to_parquet(f"{config.INMET_STATION_MONTHLY_SILVER_PATH}part-0.parquet", index=False)
    print("Estação × mês:", len(station_monthly))

    # Uma linha por estação, com os metadados do ano mais recente
    # (coordenadas às vezes são corrigidas entre anos).
    station_metadata = (
        pd.concat(stations, ignore_index=True)
        .sort_values("source_year")
        .drop_duplicates("station_code", keep="last")
        .drop(columns="source_year")
    )

    station_map = station_mapping.map_stations(
        station_metadata,
        pd.read_parquet(config.DIM_MUNICIPALITY_SILVER_PATH),
        _read_latest_mesh(root),
    )
    print_station_report(station_map)

    storage.clear_path(config.INMET_STATIONS_SILVER_PATH)
    station_map.to_parquet(f"{config.INMET_STATIONS_SILVER_PATH}part-0.parquet", index=False)


if __name__ == "__main__":
    run_pipeline()
