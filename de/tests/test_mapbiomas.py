import pandas as pd
import pytest

from epidemiological_de import ingestion
from epidemiological_de.mapbiomas import ingest, pipeline, transform

RAW = pd.DataFrame(
    {
        "ano": [2024, 2024, 2024],
        "id_municipio": ["4314902", "5101837", "4300001"],
        "area_total": [49500.0, 0.0, 98000.0],
        "area_forest": [13500.0, 0.0, 0.0],
        "area_natural_non_forest": [11650.0, 0.0, 0.0],
        "area_farming": [2400.0, 0.0, 0.0],
        "area_pasture": [0.0, 0.0, 0.0],
        "area_agriculture": [660.0, 0.0, 0.0],
        "area_urban": [19066.0, 0.0, 0.0],
        "area_water": [2649.0, 0.0, 98000.0],
    }
)


def test_query_sums_area_per_group_from_first_year():
    sql = ingest.query()

    assert "SUM(IF(nivel_2 = 'Área Urbanizada', area, 0)) AS area_urban" in sql
    assert "GROUP BY ano, id_municipio" in sql
    assert "ano >= 2015" in sql


def test_land_cover_is_share_of_mapped_area():
    land = transform.build_land_cover(RAW).set_index("municipality_code")

    assert land.loc["4314902", "land_urban_pct"] == pytest.approx(19066 / 49500 * 100)
    assert land.loc["4314902", "municipality_code_6"] == "431490"
    # Área mapeada zero: percentual nulo, não divisão por zero.
    assert pd.isna(land.loc["5101837", "land_forest_pct"])
    # Lagoa dos Patos: unidade de área do IBGE, não município.
    assert "4300001" not in land.index


class FakeBigQuery:
    def query(self, sql):
        return type("Job", (), {"to_dataframe": lambda job: RAW})()


def test_ingest_and_pipeline_end_to_end(tmp_path):
    path = ingest.run(FakeBigQuery(), root=str(tmp_path / "bronze"))
    assert ingestion.read_manifest(path)["source_type"] == "espelho"

    land = pipeline.run(root=str(tmp_path / "bronze"), silver_path=str(tmp_path / "silver"))

    assert list(land.columns) == ["municipality_code", "municipality_code_6", "year", *transform.GOLD_FEATURES]
    assert len(pd.read_parquet(tmp_path / "silver")) == 2
