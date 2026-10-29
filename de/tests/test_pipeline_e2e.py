"""
Ponta a ponta local: CSVs do INMET (bronze) -> agregado estação × mês
-> gold.pipeline.run com silvers de SIH e SINAN em parquet, sem GCS
nem BigQuery.
"""

import pandas as pd

from epidemiological_de import config
from epidemiological_de.atlas.transform import GOLD_FEATURES as ATLAS_FEATURES
from epidemiological_de.mapbiomas.transform import GOLD_FEATURES as LAND_COVER_FEATURES
from epidemiological_de.gold import pipeline as gold_pipeline
from epidemiological_de.inmet import pipeline as inmet_pipeline
from epidemiological_de.inmet.transform import aggregate_station_monthly


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


def _inmet_rows(*, date, temperature, precipitation="0,0"):
    return f"{date};1200;{precipitation};1013,2;X;X;X;{temperature};18,2;X;X;X;X;X;X;80;120;5,2;3,1;\n"


def _station_monthly(tmp_path):
    bronze_file = tmp_path / "porto_alegre.csv"
    bronze_file.write_bytes(
        (INMET_HEADER_PORTO_ALEGRE + _inmet_rows(date="2015-01-10", temperature="20,0")).encode("ISO-8859-1")
    )
    return aggregate_station_monthly(inmet_pipeline.build_inmet_silver([str(bronze_file)]))


DIM = pd.DataFrame(
    {
        "municipality_code": ["4314902", "4309209"],
        "municipality_code_6": ["431490", "430920"],
        "municipality_name": ["Porto Alegre", "Gravataí"],
        "municipality_name_normalized": ["PORTO ALEGRE", "GRAVATAI"],
        "state": ["RS", "RS"],
        "region": ["S", "S"],
        "latitude": [-30.03, -29.94],
        "longitude": [-51.23, -50.99],
    }
)

STATIONS = pd.DataFrame(
    {"station_code": ["A801"], "municipality_code_6": ["431490"], "latitude": [-30.05], "longitude": [-51.17]}
)

SIH = pd.DataFrame(
    {
        "disease": ["ASMA", "OROPOUCHE"],
        "residence_municipality_code": ["430920", "431490"],
        "occurrence_municipality_code": ["431490", "431490"],
        "year": [2015, 2015],
        "month": [2, 1],
        "hospitalizations": [4, 1],
        "is_provisional": [True, False],
    }
)

SINAN = pd.DataFrame(
    {
        "disease": ["LEPTOSPIROSE"],
        "residence_municipality_code": ["431490"],
        "occurrence_municipality_code": [None],
        "year": [2015],
        "month": [1],
        "cases": [2],
        "is_provisional": [False],
    }
)


POPULATION = pd.DataFrame(
    {
        "municipality_code_6": ["431490", "430920"],
        "year": [2015, 2015],
        "population": [1_476_867, 265_070],
        "population_density": [2981.0, 568.0],
    }
)


ATLAS = pd.DataFrame(
    {
        "municipality_code": ["4314902"],
        "municipality_code_6": ["431490"],
        "census_year": [2010],
        **{feature: [0.5] for feature in ATLAS_FEATURES},
    }
)


LAND_COVER = pd.DataFrame(
    {"municipality_code_6": ["431490"], "year": [2015], **{column: [10.0] for column in LAND_COVER_FEATURES}}
)


def _run(tmp_path):
    paths = {}
    for name, df in {"dim": DIM, "stations": STATIONS, "station_monthly": _station_monthly(tmp_path),
                     "population": POPULATION, "atlas": ATLAS, "land_cover": LAND_COVER,
                     "SIH": SIH, "SINAN": SINAN}.items():
        path = tmp_path / "silver" / f"{name}.parquet"
        path.parent.mkdir(exist_ok=True)
        df.to_parquet(path, index=False)
        paths[name] = str(path)

    gold_path = tmp_path / "gold"
    rows = gold_pipeline.run(silver_paths=paths, gold_path=str(gold_path), table_id="")
    return rows, pd.read_parquet(gold_path)


def test_gold_pipeline_builds_full_grid_for_every_disease(tmp_path):
    rows, gold = _run(tmp_path)

    # SIH: 2 municípios × 2 meses (jan-fev/2015) × 2 doenças; SINAN: 2 × 1 mês × 1.
    assert rows == len(gold) == 2 * 2 * 2 + 2 * 1 * 1
    assert set(gold["source"]) == {"SIH", "SINAN"}
    assert not gold.duplicated(["disease", "municipality_code", "year", "month"]).any()


def test_gold_pipeline_keeps_counts_and_climate(tmp_path):
    _, gold = _run(tmp_path)
    gold = gold.set_index(["disease", "municipality_code", "month"])

    assert gold.loc[("ASMA", "430920", 2), "cases"] == 4
    assert gold.loc[("ASMA", "431490", 2), "cases_by_occurrence"] == 4
    assert gold.loc[("LEPTOSPIROSE", "431490", 1), "cases"] == 2

    # Janeiro tem dado da A801: Porto Alegre usa a própria, Gravataí a mais próxima.
    assert gold.loc[("ASMA", "431490", 1), "temperature_avg_c"] == 20.0
    assert gold.loc[("ASMA", "430920", 1), "climate_source"] == "nearest_station"
    assert pd.isna(gold.loc[("ASMA", "431490", 2), "temperature_avg_c"])


def test_gold_pipeline_is_idempotent(tmp_path):
    _, first = _run(tmp_path)
    _, second = _run(tmp_path)

    pd.testing.assert_frame_equal(first, second)


def test_gold_table_default_is_the_national_one():
    assert config.BIGQUERY_GOLD_TABLE == "epidemiology_climate_monthly_br"
