import json
from datetime import date

import pandas as pd
import pytest

from epidemiological_de import config, ingestion
from epidemiological_de.sidra import ingest, pipeline, transform


def _sidra_rows(year, values):
    """Mesmo formato da API de valores do SIDRA: cabeçalho + linhas."""

    header = {"D1C": "Município (Código)", "D3C": "Ano", "V": "Valor"}
    return [header] + [{"D1C": code, "D1N": "x", "D3C": str(year), "V": value} for code, value in values.items()]


DIM = pd.DataFrame(
    {
        "municipality_code": ["4314902", "5101837"],
        "municipality_code_6": ["431490", "510183"],
        "area_km2": [495.39, 1000.0],
    }
)


def test_parse_sidra_drops_header_and_missing_values():
    df = transform.parse_sidra(_sidra_rows(2021, {"4314902": "1492530", "5101837": "..."}), transform.ESTIMATE)

    assert df.to_dict("records") == [
        {"municipality_code": "4314902", "year": 2021, "population": 1492530, "population_source": "estimativa"},
    ]


def _population():
    estimates = pd.concat(
        [
            transform.parse_sidra(_sidra_rows(2021, {"4314902": "1492530"}), transform.ESTIMATE),
            transform.parse_sidra(_sidra_rows(2024, {"4314902": "1389322", "5101837": "6000"}), transform.ESTIMATE),
        ]
    )
    census = transform.parse_sidra(_sidra_rows(2022, {"4314902": "1332570"}), transform.CENSUS)
    return transform.build_population(estimates, census, DIM).set_index(["municipality_code", "year"])


def test_census_is_used_and_gap_year_is_interpolated():
    population = _population()

    assert population.loc[("4314902", 2022), "population_source"] == "censo"
    # 2023: no meio do caminho entre o censo de 2022 e a estimativa de 2024.
    assert population.loc[("4314902", 2023), "population"] == round((1332570 + 1389322) / 2)
    assert population.loc[("4314902", 2023), "population_source"] == "interpolado"


def test_new_municipality_has_no_population_before_it_existed():
    population = _population()

    assert ("5101837", 2024) in population.index
    assert ("5101837", 2023) not in population.index


def test_density_uses_the_dim_area():
    population = _population()

    assert population.loc[("4314902", 2022), "population_density"] == pytest.approx(1332570 / 495.39)
    assert population.loc[("4314902", 2022), "municipality_code_6"] == "431490"


class FakeSession:
    def __init__(self, payloads):
        self.payloads = payloads

    def get(self, url, timeout):
        body = json.dumps(self.payloads[url]).encode()
        return type("R", (), {"status_code": 200, "content": body, "raise_for_status": lambda self: None})()


def test_ingest_downloads_every_published_year_from_first_year(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SIDRA_FIRST_YEAR", 2021)
    payloads = {
        config.SIDRA_ESTIMATE_YEARS_URL: _sidra_rows(0, {}) + [{"D3C": y} for y in ("2014", "2021", "2024")],
        config.SIDRA_ESTIMATES_URL.format(year=2021): _sidra_rows(2021, {"4314902": "1492530"}),
        config.SIDRA_ESTIMATES_URL.format(year=2024): _sidra_rows(2024, {"4314902": "1389322"}),
        config.SIDRA_CENSUS_2022_URL: _sidra_rows(2022, {"4314902": "1332570"}),
    }

    written = ingest.run(FakeSession(payloads), root=str(tmp_path))

    assert sorted(written) == ["populacao_censo_2022.json", "populacao_estimada_2021.json", "populacao_estimada_2024.json"]
    assert ingestion.read_manifest(written["populacao_estimada_2024.json"])["source_type"] == "oficial"


def test_pipeline_reads_latest_snapshot_of_each_file(tmp_path):
    def save(filename, rows, day):
        ingestion.save_snapshot(
            json.dumps(rows).encode(), source="sidra", filename=filename, url="x",
            source_type="oficial", ingestion_date=day, root=str(tmp_path / "bronze"),
        )

    save("populacao_estimada_2024.json", _sidra_rows(2024, {"4314902": "1", "5101837": "1"}), date(2025, 8, 1))
    # Revisão da estimativa de 2024 num snapshot mais novo; o censo não mudou.
    save("populacao_estimada_2024.json", _sidra_rows(2024, {"4314902": "1389322", "5101837": "6000"}), date(2026, 8, 1))
    save("populacao_censo_2022.json", _sidra_rows(2022, {"4314902": "1332570", "5101837": "5000"}), date(2025, 8, 1))

    dim_path = tmp_path / "dim.parquet"
    DIM.to_parquet(dim_path, index=False)

    population = pipeline.run(
        root=str(tmp_path / "bronze"), silver_path=str(tmp_path / "silver"), dim_path=str(dim_path)
    ).set_index(["municipality_code", "year"])

    assert population.loc[("4314902", 2024), "population"] == 1389322
    stored = pd.read_parquet(tmp_path / "silver")
    assert len(stored) == len(population)
