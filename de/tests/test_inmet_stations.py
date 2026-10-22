import pandas as pd

from epidemiological_de.inmet.stations import map_stations, name_candidates


def _square(lon, lat, size=0.5):
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat],
        ]],
    }


# Dois municípios do RS lado a lado e um de SC.
DIM = pd.DataFrame(
    {
        "municipality_code": ["4314902", "4304606", "4205407"],
        "municipality_name": ["Porto Alegre", "Canoas", "Florianópolis"],
        "municipality_name_normalized": ["PORTO ALEGRE", "CANOAS", "FLORIANOPOLIS"],
        "state": ["RS", "RS", "SC"],
        "latitude": [-29.75, -29.75, -27.25],
        "longitude": [-51.25, -50.75, -48.25],
    }
)

MESH = {
    "features": [
        {"properties": {"codarea": "4314902"}, "geometry": _square(-51.5, -30.0)},
        {"properties": {"codarea": "4304606"}, "geometry": _square(-51.0, -30.0)},
        {"properties": {"codarea": "4205407"}, "geometry": _square(-48.5, -27.5)},
    ]
}


def _stations(*rows):
    return pd.DataFrame(rows, columns=["station_code", "station_name", "state", "latitude", "longitude"])


def test_name_candidates_tries_full_name_before_splitting():
    assert name_candidates("Embu-Guaçu") == ["EMBU-GUACU", "EMBU"]
    assert name_candidates("PORTO ALEGRE - JARDIM BOTANICO")[1] == "PORTO ALEGRE"
    assert "PORTO ALEGRE" in name_candidates("PORTO ALEGRE- BELEM NOVO")
    assert "BELO HORIZONTE" in name_candidates("BELO HORIZONTE (PAMPULHA)")


def test_name_wins_over_polygon_when_station_sits_in_neighbor():
    # Estação "PORTO ALEGRE" fisicamente dentro do quadrado de Canoas.
    mapped = map_stations(_stations(("A801", "PORTO ALEGRE - JARDIM BOTANICO", "RS", -29.8, -50.8)), DIM, MESH)

    row = mapped.iloc[0]
    assert row["municipality_code"] == "4314902"
    assert row["municipality_code_6"] == "431490"
    assert row["match_method"] == "name"


def test_polygon_used_when_name_does_not_match():
    mapped = map_stations(_stations(("A999", "MAL. CANDIDO RONDON", "RS", -29.8, -50.8)), DIM, MESH)

    assert mapped.iloc[0]["municipality_code"] == "4304606"
    assert mapped.iloc[0]["match_method"] == "polygon"


def test_nearest_in_same_state_for_points_outside_any_polygon():
    # No mar, a leste de Florianópolis: fora de qualquer polígono.
    mapped = map_stations(_stations(("A888", "FAROL", "SC", -27.3, -47.0)), DIM, MESH)

    row = mapped.iloc[0]
    assert row["municipality_code"] == "4205407"
    assert row["match_method"] == "nearest"
    assert row["distance_km"] > 0


def test_name_match_is_scoped_to_the_station_state():
    # "CANOAS" em SC não pode casar com Canoas/RS pelo nome.
    mapped = map_stations(_stations(("A777", "CANOAS", "SC", -27.3, -48.3)), DIM, MESH)

    assert mapped.iloc[0]["municipality_code"] == "4205407"
    assert mapped.iloc[0]["match_method"] == "polygon"
