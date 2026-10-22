"""
Estação do INMET -> município (código IBGE).

Ordem de decisão, medida contra as 565 estações do zip de 2024:

1. Nome: o INMET nomeia a estação pelo município que ela representa
   ("PORTO ALEGRE - JARDIM BOTANICO"). Casou 525. Preferido ao ponto
   geográfico porque ~16 delas ficam fisicamente no vizinho (a
   "FLORIANOPOLIS" está em São José, a "MOSTARDAS" em Tavares) e
   perderiam o vínculo com o município que dá nome à série.
2. Ponto no polígono (malha intermediária do IBGE): para as que o nome
   não resolve -- abreviações ("MAL. CANDIDO RONDON"), grafias
   diferentes ("ARCO VERDE"), localidades ("PICO DO COUTO").
3. Centróide mais próximo na mesma UF: estações costeiras/ilhas que
   caem fora de qualquer polígono (Abrolhos, Forte de Copacabana).
"""

import math
import re

import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from epidemiological_de.ibge.transform import normalize_name

STATION_COLUMNS = [
    "station_code",
    "station_name",
    "state",
    "latitude",
    "longitude",
    "municipality_code",
    "municipality_code_6",
    "municipality_name",
    "match_method",
    "distance_km",
]


def name_candidates(station_name: str) -> list[str]:
    """
    Formas do nome a tentar, da mais completa para a mais curta. O nome
    inteiro vem primeiro para não quebrar municípios com hífen no nome
    (ex.: "EMBU-GUACU").
    """

    normalized = normalize_name(station_name)
    candidates = [normalized]

    for separator in (r"\s+-\s*|\s*-\s+", r"\s*\(", r"-"):
        head = re.split(separator, normalized, maxsplit=1)[0].strip()
        if head and head not in candidates:
            candidates.append(head)

    return candidates


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def map_stations(
    stations: pd.DataFrame,
    dim_municipality: pd.DataFrame,
    mesh: dict,
) -> pd.DataFrame:
    """
    `stations`: uma linha por estação (station_code, station_name,
    state, latitude, longitude). `mesh`: GeoJSON da malha municipal do
    IBGE (properties.codarea = código de 7 dígitos).
    """

    by_name = {
        (row.state, row.municipality_name_normalized): row.municipality_code
        for row in dim_municipality.itertuples()
    }
    municipalities = dim_municipality.set_index("municipality_code")

    geometries = [shape(feature["geometry"]) for feature in mesh["features"]]
    mesh_codes = [str(feature["properties"]["codarea"]) for feature in mesh["features"]]
    tree = STRtree(geometries)

    rows = []
    for station in stations.itertuples():
        code, method = None, None

        for candidate in name_candidates(station.station_name or ""):
            code = by_name.get((station.state, candidate))
            if code is not None:
                method = "name"
                break

        if code is None:
            point = Point(station.longitude, station.latitude)
            hits = tree.query(point, predicate="intersects")
            if len(hits):
                code, method = mesh_codes[hits[0]], "polygon"

        if code is None:
            same_state = municipalities[
                (municipalities["state"] == station.state)
                & municipalities["latitude"].notna()
            ]
            if not same_state.empty:
                distances = same_state.apply(
                    lambda m: _haversine_km(station.latitude, station.longitude, m.latitude, m.longitude),
                    axis=1,
                )
                code, method = distances.idxmin(), "nearest"

        municipality = municipalities.loc[code] if code is not None else None

        rows.append(
            {
                "station_code": station.station_code,
                "station_name": station.station_name,
                "state": station.state,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "municipality_code": code,
                "municipality_code_6": code[:6] if code is not None else None,
                "municipality_name": municipality["municipality_name"] if municipality is not None else None,
                "match_method": method,
                # Distância até o centróide do município atribuído: um
                # valor alto aponta associação a revisar.
                "distance_km": (
                    round(_haversine_km(station.latitude, station.longitude, municipality["latitude"], municipality["longitude"]), 1)
                    if municipality is not None and pd.notna(municipality["latitude"])
                    else None
                ),
            }
        )

    return pd.DataFrame(rows, columns=STATION_COLUMNS)
