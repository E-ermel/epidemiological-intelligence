import pandas as pd

from epidemiological_de import ingestion
from epidemiological_de.snis import ingest, pipeline, transform

DIM = pd.DataFrame(
    {
        "municipality_code": ["4314902", "5101837", "1500602"],
        "municipality_code_6": ["431490", "510183", "150060"],
    }
)


def _raw(rows):
    """rows: (ano, id_municipio, cobertura de água)."""

    raw = pd.DataFrame(rows, columns=["ano", "id_municipio", "indice_atendimento_total_agua"])
    for column in ingest.INDICATORS:
        if column not in raw:
            raw[column] = 50.0
    return raw


RAW = _raw(
    [
        (2014, "4314902", 98.0),
        (2016, "4314902", 100.0),
        (2022, "4314902", 99.0),
        (2010, "5101837", 40.0),
    ]
)


def _sanitation():
    return transform.build_sanitation(
        transform.parse_snis(RAW), DIM, first_year=2015, last_year=2027, max_carry_years=4
    ).set_index(["municipality_code", "year"])


def test_query_selects_indicators_with_carry_window():
    sql = ingest.query()

    assert "indice_perda_distribuicao_agua" in sql
    assert "ano >= 2011" in sql


def test_year_without_report_uses_latest_previous_report():
    df = _sanitation()

    assert df.loc[("4314902", 2015), "snis_water_coverage_pct"] == 98.0
    assert df.loc[("4314902", 2015), "snis_reference_year"] == 2014
    assert df.loc[("4314902", 2016), "snis_water_coverage_pct"] == 100.0
    assert df.loc[("4314902", 2026), "snis_reference_year"] == 2022


def test_report_older_than_carry_window_is_null():
    df = _sanitation()

    assert pd.isna(df.loc[("4314902", 2027), "snis_water_coverage_pct"])
    # Último dado de 2010: fora da janela de 4 anos já em 2015.
    assert pd.isna(df.loc[("5101837", 2015), "snis_water_coverage_pct"])
    assert pd.isna(df.loc[("1500602", 2020), "snis_reference_year"])
    assert len(df) == len(DIM) * 13


class FakeBigQuery:
    def query(self, sql):
        return type("Job", (), {"to_dataframe": lambda job: RAW})()


def test_ingest_and_pipeline_end_to_end(tmp_path):
    path = ingest.run(FakeBigQuery(), root=str(tmp_path / "bronze"))
    assert ingestion.read_manifest(path)["source_type"] == "espelho"

    dim_path = tmp_path / "dim.parquet"
    DIM.to_parquet(dim_path, index=False)
    df = pipeline.run(
        root=str(tmp_path / "bronze"), silver_path=str(tmp_path / "silver"), dim_path=str(dim_path), last_year=2024
    )

    assert list(df.columns) == ["municipality_code", "municipality_code_6", "year", *transform.GOLD_FEATURES]
    assert len(pd.read_parquet(tmp_path / "silver")) == len(DIM) * 10
