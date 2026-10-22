import unicodedata

import pandas as pd

DIM_COLUMNS = [
    "municipality_code",
    "municipality_code_6",
    "municipality_name",
    "municipality_name_normalized",
    "state_code",
    "state",
    "state_name",
    "region",
    "region_name",
    "latitude",
    "longitude",
    "area_km2",
]


def normalize_name(name: str) -> str:
    """
    Mesmo formato dos nomes que vêm do TabNet/SINAN e do INMET
    ("BENTO GONCALVES"): maiúsculas, sem acento. Serve para casar com
    as fontes atuais, que ainda juntam por nome.
    """

    without_accents = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    return " ".join(without_accents.upper().split())


def _uf(municipio: dict) -> dict:
    # Municípios recém-criados podem vir sem microrregião (ex.: Boa
    # Esperança do Norte/MT, 2024); a região imediata está sempre
    # presente e leva à mesma UF.
    microrregiao = municipio.get("microrregiao")
    if microrregiao:
        return microrregiao["mesorregiao"]["UF"]

    return municipio["regiao-imediata"]["regiao-intermediaria"]["UF"]


def build_dim_municipality(municipios: list[dict], metadados: list[dict]) -> pd.DataFrame:
    rows = []
    for municipio in municipios:
        uf = _uf(municipio)
        code = str(municipio["id"])

        rows.append(
            {
                "municipality_code": code,
                # DATASUS (SIH, SINAN, CNES) usa o código sem o dígito
                # verificador: os 6 primeiros dígitos.
                "municipality_code_6": code[:6],
                "municipality_name": municipio["nome"],
                "municipality_name_normalized": normalize_name(municipio["nome"]),
                "state_code": str(uf["id"]),
                "state": uf["sigla"],
                "state_name": uf["nome"],
                "region": uf["regiao"]["sigla"],
                "region_name": uf["regiao"]["nome"],
            }
        )

    dim = pd.DataFrame(rows)

    geo = pd.DataFrame(
        [
            {
                "municipality_code": str(item["id"]),
                "latitude": float(item["centroide"]["latitude"]),
                "longitude": float(item["centroide"]["longitude"]),
                "area_km2": float(item["area"]["dimensao"]),
            }
            for item in metadados
        ]
    )

    # LEFT: a lista de municípios é a referência. Município sem malha
    # ainda (criado depois da última malha) fica com lat/lon/área nulos,
    # e o relatório de qualidade mostra quantos são.
    dim = dim.merge(geo, on="municipality_code", how="left", validate="one_to_one")

    return dim[DIM_COLUMNS].sort_values("municipality_code").reset_index(drop=True)
