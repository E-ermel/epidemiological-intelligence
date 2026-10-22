from epidemiological_de.inmet import pipeline


HEADER = (
    "REGIAO:;S\n"
    "UF:;RS\n"
    "ESTACAO:;PORTO ALEGRE - JARDIM BOTANICO\n"
    "CODIGO (WMO):;A801\n"
    "LATITUDE:;-30,05\n"
    "LONGITUDE:;-51,17\n"
    "ALTITUDE:;41,18\n"
    "DATA DE FUNDACAO:;01/01/2000\n"
)

DATA_ROW = "2023-01-01;0000 UTC;0,0;1013,2;X;X;X;25,4;18,2;X;X;X;X;X;X;80;120;5,2;3,1;\n"


def _write_bronze_file(path, header=HEADER, rows=(DATA_ROW,)):
    path.write_bytes((header + "".join(rows)).encode("ISO-8859-1"))


def test_parse_inmet_file_reads_bronze_csv_end_to_end(tmp_path):
    file_path = tmp_path / "INMET_S_RS_A801_PORTO ALEGRE_01-01-2023.CSV"
    _write_bronze_file(file_path)

    df = pipeline.parse_inmet_file(str(file_path))

    assert len(df) == 1
    assert df.loc[0, "municipality"] == "PORTO ALEGRE - JARDIM BOTANICO"
    assert df.loc[0, "temperature_c"] == 25.4


def test_build_inmet_silver_preserves_total_record_count_across_files(tmp_path):
    file_a = tmp_path / "station_a.csv"
    file_b = tmp_path / "station_b.csv"
    _write_bronze_file(file_a, rows=(DATA_ROW, DATA_ROW))
    _write_bronze_file(file_b, rows=(DATA_ROW,))

    df = pipeline.build_inmet_silver([str(file_a), str(file_b)])

    assert len(df) == 3
    assert "year" in df.columns


def test_build_inmet_silver_raises_when_no_files_given():
    try:
        pipeline.build_inmet_silver([])
    except ValueError:
        return

    raise AssertionError("expected ValueError for empty file list")


def _write_year_zip(path, stations):
    """stations: {nome_do_csv_no_zip: (header, rows)}"""
    import zipfile

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, (header, rows) in stations.items():
            archive.writestr(name, (header + "".join(rows)).encode("ISO-8859-1"))


HEADER_SC = HEADER.replace("UF:;RS", "UF:;SC").replace("A801", "A806").replace(
    "PORTO ALEGRE - JARDIM BOTANICO", "FLORIANOPOLIS"
)


def test_list_year_zips_finds_partitioned_zips(tmp_path):
    _write_year_zip(tmp_path / "inmet" / "year=2024" / "2024.zip", {})
    _write_year_zip(tmp_path / "inmet" / "year=2023" / "2023.zip", {})

    found = pipeline.list_year_zips(root=str(tmp_path))

    assert [year for year, _ in found] == [2023, 2024]


def test_process_year_writes_silver_and_returns_station_monthly(tmp_path):
    import pandas as pd

    zip_path = tmp_path / "bronze" / "inmet" / "year=2023" / "2023.zip"
    _write_year_zip(
        zip_path,
        {
            "INMET_S_RS_A801_PORTO ALEGRE_01-01-2023_A_31-12-2023.CSV": (HEADER, (DATA_ROW, DATA_ROW.replace("0000 UTC", "0100 UTC"))),
            # Estação sem dado de temperatura nenhum: coluna toda nula
            # precisa ser alinhada ao schema do primeiro arquivo.
            "INMET_S_SC_A806_FLORIANOPOLIS_01-01-2023_A_31-12-2023.CSV": (HEADER_SC, (DATA_ROW.replace("25,4", "-9999"),)),
        },
    )
    silver_root = str(tmp_path / "silver" / "inmet")

    station_monthly, stations = pipeline.process_year(str(zip_path), 2023, silver_root)

    silver = pd.read_parquet(silver_root)
    assert len(silver) == 3
    assert set(silver["station_code"]) == {"A801", "A806"}
    assert int(silver["year"].astype(int).iloc[0]) == 2023

    a801 = station_monthly[station_monthly["station_code"] == "A801"].iloc[0]
    assert (a801["year"], a801["month"]) == (2023, 1)
    assert a801["temperature_avg_c"] == 25.4

    assert set(stations["state"]) == {"RS", "SC"}


def test_process_year_replaces_previous_partition(tmp_path):
    import pandas as pd

    zip_path = tmp_path / "2023.zip"
    _write_year_zip(zip_path, {"INMET_S_RS_A801_X_01-01-2023.CSV": (HEADER, (DATA_ROW,))})
    silver_root = str(tmp_path / "silver")

    pipeline.process_year(str(zip_path), 2023, silver_root)
    pipeline.process_year(str(zip_path), 2023, silver_root)

    assert len(pd.read_parquet(silver_root)) == 1
