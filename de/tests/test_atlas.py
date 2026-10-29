import pandas as pd
import pytest

from epidemiological_de import ingestion
from epidemiological_de.atlas import ingest, pipeline, transform


def _raw(**overrides):
    row = {column: 1.0 for column in ingest.COLUMNS}
    row.update(ano=2010, id_municipio="4314902", idhm=0.805, populacao_urbana=900, populacao_rural=100)
    row.update(overrides)
    return row


def test_build_atlas_renames_and_computes_urban_share():
    atlas = transform.build_atlas(pd.DataFrame([_raw(), _raw(ano=2000, idhm=0.744)]))

    latest = atlas[atlas["census_year"] == 2010].iloc[0]
    assert latest["municipality_code_6"] == "431490"
    assert latest["idhm"] == 0.805
    assert latest["pct_urban"] == pytest.approx(90.0)


def test_latest_census_keeps_only_2010_with_prefixed_columns():
    atlas = transform.build_atlas(pd.DataFrame([_raw(), _raw(ano=2000, idhm=0.744)]))

    latest = transform.latest_census(atlas)

    assert len(latest) == 1
    assert latest.iloc[0]["atlas_idhm"] == 0.805
    assert set(latest.columns) == {"municipality_code_6", *(f"atlas_{f}" for f in transform.GOLD_FEATURES)}


class FakeBigQuery:
    def __init__(self, df):
        self.df, self.sql = df, None

    def query(self, sql):
        self.sql = sql
        return type("Job", (), {"to_dataframe": lambda job: self.df})()


def test_ingest_saves_csv_snapshot_marked_as_mirror(tmp_path):
    client = FakeBigQuery(pd.DataFrame([_raw()]))

    path = ingest.run(client, root=str(tmp_path))

    assert "mundo_onu_adh.municipio" in client.sql
    manifest = ingestion.read_manifest(path)
    assert manifest["source_type"] == "espelho"
    # Mesma resposta de novo: nada novo gravado.
    assert ingest.run(client, root=str(tmp_path)) is None


def test_pipeline_writes_silver_from_latest_snapshot(tmp_path):
    ingest.run(FakeBigQuery(pd.DataFrame([_raw()])), root=str(tmp_path / "bronze"))

    atlas = pipeline.run(root=str(tmp_path / "bronze"), silver_path=str(tmp_path / "silver"))

    assert len(pd.read_parquet(tmp_path / "silver")) == len(atlas) == 1
