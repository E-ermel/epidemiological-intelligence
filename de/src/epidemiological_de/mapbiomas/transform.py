"""
Áreas por grupo do MapBiomas -> percentual do território por município × ano.

O percentual é sobre a área mapeada do município naquele ano (soma de
todas as classes), não sobre a área oficial do IBGE: as duas diferem um
pouco nas bordas, e o percentual fica consistente com a própria fonte.

As lagoas dos Patos e Mirim (4300001 e 4300002) vêm na fonte como se
fossem municípios, mas são unidades de área do IBGE: ficam de fora (as
duas têm o mesmo código de 6 dígitos, 430000, e duplicariam o gold).
"""

import pandas as pd

from epidemiological_de.mapbiomas.ingest import GROUPS

# area_forest -> land_forest_pct, ...
GOLD_FEATURES = [f"land_{column.removeprefix('area_')}_pct" for column in GROUPS]


def build_land_cover(raw: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "municipality_code": raw["id_municipio"].astype(str).str.zfill(7),
            "year": raw["ano"].astype(int),
        }
    )
    df["municipality_code_6"] = df["municipality_code"].str[:6]
    df = df[df["municipality_code"].str[2:6] != "0000"]
    raw = raw.loc[df.index]

    total = raw["area_total"].where(raw["area_total"] > 0)
    for column, feature in zip(GROUPS, GOLD_FEATURES):
        df[feature] = raw[column] / total * 100

    return df[["municipality_code", "municipality_code_6", "year", *GOLD_FEATURES]]
