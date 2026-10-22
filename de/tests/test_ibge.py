import json

import pytest

from epidemiological_de import ingestion
from epidemiological_de.ibge import ingest, pipeline
from epidemiological_de.ibge.transform import build_dim_municipality, normalize_name

RS = {"id": 43, "sigla": "RS", "nome": "Rio Grande do Sul", "regiao": {"id": 4, "sigla": "S", "nome": "Sul"}}
MT = {"id": 51, "sigla": "MT", "nome": "Mato Grosso", "regiao": {"id": 5, "sigla": "CO", "nome": "Centro-Oeste"}}

# Mesmo formato da API de Localidades do IBGE.
MUNICIPIOS = [
    {
        "id": 4314902,
        "nome": "Porto Alegre",
        "microrregiao": {"id": 43026, "nome": "Porto Alegre", "mesorregiao": {"id": 4305, "nome": "Metropolitana", "UF": RS}},
        "regiao-imediata": {"id": 430001, "nome": "Porto Alegre", "regiao-intermediaria": {"id": 4301, "nome": "Porto Alegre", "UF": RS}},
    },
    {
        "id": 4302105,
        "nome": "Bento Gonçalves",
        "microrregiao": {"id": 43016, "nome": "Caxias do Sul", "mesorregiao": {"id": 4302, "nome": "Nordeste", "UF": RS}},
        "regiao-imediata": {"id": 430005, "nome": "Bento Gonçalves", "regiao-intermediaria": {"id": 4302, "nome": "Caxias do Sul", "UF": RS}},
    },
    # Criado em 2024: sem microrregião e ainda fora da malha.
    {
        "id": 5101837,
        "nome": "Boa Esperança do Norte",
        "microrregiao": None,
        "regiao-imediata": {"id": 510010, "nome": "Sorriso", "regiao-intermediaria": {"id": 5103, "nome": "Sinop", "UF": MT}},
    },
]

# Mesmo formato da API de metadados da malha.
METADADOS = [
    {"id": "4314902", "centroide": {"longitude": -51.17, "latitude": -30.08}, "area": {"dimensao": "495.390", "unidade": {"id": "km2"}}},
    {"id": "4302105", "centroide": {"longitude": -51.52, "latitude": -29.17}, "area": {"dimensao": "274.070", "unidade": {"id": "km2"}}},
]


def test_normalize_name_matches_tabnet_style():
    assert normalize_name("Bento Gonçalves") == "BENTO GONCALVES"
    assert normalize_name("  Alta Floresta  D'Oeste ") == "ALTA FLORESTA D'OESTE"


def test_dim_has_both_codes_and_geography():
    dim = build_dim_municipality(MUNICIPIOS, METADADOS)
    poa = dim.set_index("municipality_code").loc["4314902"]

    assert poa["municipality_code_6"] == "431490"
    assert poa["state"] == "RS"
    assert poa["region"] == "S"
    assert poa["municipality_name_normalized"] == "PORTO ALEGRE"
    assert poa["area_km2"] == pytest.approx(495.39)
    assert poa["latitude"] == pytest.approx(-30.08)


def test_municipality_without_microregion_or_mesh_is_kept_with_null_geo():
    dim = build_dim_municipality(MUNICIPIOS, METADADOS)
    new_one = dim.set_index("municipality_code").loc["5101837"]

    assert len(dim) == len(MUNICIPIOS)
    assert new_one["state"] == "MT"
    assert new_one["region"] == "CO"
    assert new_one[["latitude", "longitude", "area_km2"]].isna().all()


def test_quality_check_rejects_truncated_response():
    dim = build_dim_municipality(MUNICIPIOS, METADADOS)

    with pytest.raises(ValueError):
        pipeline.check_quality(dim)


class StaticSession:
    def __init__(self, payloads):
        self.payloads = payloads

    def get(self, url, timeout):
        return type("R", (), {"status_code": 200, "content": self.payloads[url], "raise_for_status": lambda self: None})()


def test_ingest_writes_both_files_then_noops_when_unchanged(tmp_path):
    session = StaticSession(
        {
            ingest.FILES[ingest.MUNICIPIOS_FILE]: json.dumps(MUNICIPIOS).encode(),
            ingest.FILES[ingest.MALHA_METADADOS_FILE]: json.dumps(METADADOS).encode(),
        }
    )

    first = ingest.run(session=session, root=str(tmp_path))
    second = ingest.run(session=session, root=str(tmp_path))

    assert all(path is not None for path in first.values())
    assert all(path is None for path in second.values())
    assert ingestion.read_manifest(first[ingest.MUNICIPIOS_FILE])["source_type"] == "oficial"
