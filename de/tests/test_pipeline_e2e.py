import pandas as pd

from epidemiological_de.gold.transform import build_gold
from epidemiological_de.inmet import pipeline as inmet_pipeline
from epidemiological_de.sinan import transform as sinan_transform


INMET_HEADER_PORTO_ALEGRE = (
    "REGIAO:;S\n"
    "UF:;RS\n"
    "ESTACAO:;PORTO ALEGRE - JARDIM BOTANICO\n"
    "CODIGO (WMO):;A801\n"
    "LATITUDE:;-30,05\n"
    "LONGITUDE:;-51,17\n"
    "ALTITUDE:;41,18\n"
    "DATA DE FUNDACAO:;01/01/2000\n"
)

INMET_HEADER_CANOAS = (
    "REGIAO:;S\n"
    "UF:;RS\n"
    "ESTACAO:;CANOAS\n"
    "CODIGO (WMO):;A802\n"
    "LATITUDE:;-29,92\n"
    "LONGITUDE:;-51,18\n"
    "ALTITUDE:;5,0\n"
    "DATA DE FUNDACAO:;01/01/2000\n"
)


def _inmet_rows(*, date, temperature, precipitation="0,0"):
    return f"{date};1200;{precipitation};1013,2;X;X;X;{temperature};18,2;X;X;X;X;X;X;80;120;5,2;3,1;\n"


def _write_bronze_file(path, header, rows):
    path.write_bytes((header + "".join(rows)).encode("ISO-8859-1"))


def _build_inmet_silver(tmp_path):
    porto_alegre_file = tmp_path / "porto_alegre.csv"
    canoas_file = tmp_path / "canoas.csv"

    _write_bronze_file(
        porto_alegre_file,
        INMET_HEADER_PORTO_ALEGRE,
        [_inmet_rows(date="2023-01-10", temperature="20,0")],
    )
    _write_bronze_file(
        canoas_file,
        INMET_HEADER_CANOAS,
        [_inmet_rows(date="2023-01-15", temperature="24,0")],
    )

    return inmet_pipeline.build_inmet_silver(
        [str(porto_alegre_file), str(canoas_file)]
    )


def _build_sinan_silver():
    raw = pd.DataFrame(
        {
            "municipio": ["431490 PORTO ALEGRE", "999999 SEM ESTACAO"],
            "2023/Jan": ["10", "3"],
        }
    )
    return sinan_transform.process_sinan_file(raw, "ASMA", "asma.csv")


def test_bronze_to_gold_preserves_sinan_cardinality_with_small_fixtures(tmp_path):
    inmet_silver = _build_inmet_silver(tmp_path)
    sinan_silver = _build_sinan_silver()

    gold_df = build_gold(inmet_silver, sinan_silver)

    assert len(gold_df) == len(sinan_silver)


def test_bronze_to_gold_attaches_climate_only_where_a_station_exists(tmp_path):
    inmet_silver = _build_inmet_silver(tmp_path)
    sinan_silver = _build_sinan_silver()

    gold_df = build_gold(inmet_silver, sinan_silver)

    porto_alegre_row = gold_df[gold_df["municipality"] == "PORTO ALEGRE"].iloc[0]
    assert porto_alegre_row["temperature_avg_c"] == 20.0
    assert porto_alegre_row["cases"] == 10

    no_station_row = gold_df[gold_df["municipality"] == "SEM ESTACAO"].iloc[0]
    assert pd.isna(no_station_row["temperature_avg_c"])
    assert no_station_row["cases"] == 3


def test_bronze_to_gold_has_no_duplicate_keys(tmp_path):
    inmet_silver = _build_inmet_silver(tmp_path)
    sinan_silver = _build_sinan_silver()

    gold_df = build_gold(inmet_silver, sinan_silver)

    duplicate_counts = gold_df.groupby(
        ["disease", "municipality", "year", "month"]
    ).size()
    assert (duplicate_counts <= 1).all()


def test_bronze_to_gold_is_idempotent_when_run_twice(tmp_path):
    inmet_silver = _build_inmet_silver(tmp_path)
    sinan_silver = _build_sinan_silver()

    first_run = build_gold(inmet_silver, sinan_silver)
    second_run = build_gold(inmet_silver, sinan_silver)

    pd.testing.assert_frame_equal(first_run, second_run)
