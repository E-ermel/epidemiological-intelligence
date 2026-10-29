import json

import pandas as pd
import pytest

from epidemiological_de import config, ingestion
from epidemiological_de.prodes import ingest, pipeline, transform

DIM = pd.DataFrame(
    {
        "municipality_code": ["4314902", "5101837", "1500602"],
        "municipality_code_6": ["431490", "510183", "150060"],
        "area_km2": [495.4, 1000.0, 0.0],
    }
)

MUN, UF = 2, 1


def _period(start, end, features):
    return {
        "startDate": {"year": start, "month": 8, "day": 1},
        "endDate": {"year": end, "month": 7, "day": 31},
        "features": [{"loi": loi, "loiname": gid, "areas": [{"type": 1, "area": area}]} for loi, gid, area in features],
    }


def _loinames(municipalities):
    return {
        "lois": [
            {"gid": UF, "name": "uf", "loinames": [{"gid": 99, "loiname": "Rio Grande do Sul"}]},
            {"gid": MUN, "name": "mun", "loinames": [{"gid": gid, "loiname": "x", "codibge": int(code)} for gid, code in municipalities.items()]},
        ]
    }


# Pampa: acumulado até 2000, bienal 2014-2016, anual depois; sem 2026.
PAMPA = (
    {
        "periods": [
            _period(1500, 2000, [(MUN, 10, 500.0)]),
            _period(2014, 2016, [(MUN, 10, 4.0), (UF, 99, 4.0)]),
            _period(2016, 2017, [(MUN, 10, 1.0)]),
        ]
    },
    _loinames({10: "4314902"}),
)

# Cerrado já publicou 2017 e o preliminar de 2018.
CERRADO = (
    {
        "periods": [
            _period(2016, 2017, [(MUN, 20, 2.0), (MUN, 21, 3.0)]),
            _period(2017, 2018, [(MUN, 21, 5.0)]),
        ]
    },
    _loinames({20: "5101837", 21: "4314902"}),
)


def _biomes():
    return [transform.parse_biome(data, loinames, first_year=2015) for data, loinames in (PAMPA, CERRADO)]


def test_multi_year_period_is_split_and_cumulative_baseline_is_dropped():
    df, members, published = transform.parse_biome(*PAMPA, first_year=2015)
    by_year = df.set_index("year")["deforestation_km2"]

    assert published == {2015, 2016, 2017}
    # Bienal 2014-2016: metade para cada ano; o recorte de UF não entra.
    assert by_year[2015] == 2.0
    assert by_year[2016] == 2.0
    assert members == {"4314902"}
    assert 2000 not in by_year.index


def test_municipality_in_two_biomes_is_summed_and_absent_is_zero():
    df = transform.build_deforestation(_biomes(), DIM).set_index(["municipality_code", "year"])

    assert df.loc[("4314902", 2017), "deforestation_km2"] == 4.0
    assert df.loc[("4314902", 2017), "deforestation_pct"] == pytest.approx(4.0 / 495.4 * 100)
    assert df.loc[("5101837", 2018), "deforestation_km2"] == 0.0
    # Município fora dos dois biomas do fixture: zero.
    assert df.loc[("1500602", 2017), "deforestation_km2"] == 0.0
    assert pd.isna(df.loc[("1500602", 2017), "deforestation_pct"])


def test_year_missing_in_one_of_the_municipality_biomes_is_null():
    df = transform.build_deforestation(_biomes(), DIM).set_index(["municipality_code", "year"])

    # 2018 só existe no Cerrado; Porto Alegre também é Pampa: nulo, não parcial.
    assert pd.isna(df.loc[("4314902", 2018), "deforestation_km2"])
    # Antes de 2017 o Cerrado do fixture não tem dado.
    assert pd.isna(df.loc[("5101837", 2016), "deforestation_km2"])


class FakeSession:
    def get(self, url, timeout):
        body = json.dumps({"url": url}).encode()
        return type("R", (), {"status_code": 200, "content": body, "raise_for_status": lambda self: None})()


def test_ingest_saves_data_and_names_for_every_biome(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PRODES_BIOMES", ["pampa", "cerrado"])

    written = ingest.run(FakeSession(), root=str(tmp_path))

    assert sorted(written) == [
        "prodes_cerrado_data.json",
        "prodes_cerrado_loinames.json",
        "prodes_pampa_data.json",
        "prodes_pampa_loinames.json",
    ]
    manifest = ingestion.read_manifest(written["prodes_pampa_data.json"])
    assert manifest["source_type"] == "oficial"
    assert manifest["url"].endswith("/data/prodes_pampa.json")


def test_pipeline_writes_silver_from_bronze(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PRODES_BIOMES", ["pampa", "cerrado"])
    for biome, (data, loinames) in {"pampa": PAMPA, "cerrado": CERRADO}.items():
        for filename, payload in ((ingest.data_file(biome), data), (ingest.loinames_file(biome), loinames)):
            ingestion.save_snapshot(
                json.dumps(payload).encode(), source="prodes", filename=filename, url="x",
                source_type="oficial", root=str(tmp_path / "bronze"),
            )
    dim_path = tmp_path / "dim.parquet"
    DIM.to_parquet(dim_path, index=False)

    df = pipeline.run(root=str(tmp_path / "bronze"), silver_path=str(tmp_path / "silver"), dim_path=str(dim_path))

    stored = pd.read_parquet(tmp_path / "silver")
    assert len(stored) == len(df) == len(DIM) * 4
    assert list(stored.columns) == ["municipality_code", "municipality_code_6", "year", *transform.GOLD_FEATURES]
