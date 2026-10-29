"""
Indicadores do SNIS -> saneamento por município × ano.

- Cada ano recebe o último ano de referência que o município informou,
  até config.SNIS_MAX_CARRY_YEARS para trás: cobre os anos em que ele
  não respondeu e os anos depois de 2022 (fim do SNIS).
  `snis_reference_year` diz de que ano vieram os valores.
- Indicadores de esgoto só existem onde há prestador de esgoto (cerca de
  metade dos municípios); nos demais ficam nulos, não zero -- o SNIS
  não diz se o município não tem rede ou só não respondeu.
- Valores como a fonte publica (inclusive perdas negativas, que
  aparecem em poucos municípios).
"""

import pandas as pd

from epidemiological_de.snis.ingest import INDICATORS

GOLD_FEATURES = [f"snis_{name}" for name in INDICATORS.values()] + ["snis_reference_year"]


def parse_snis(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns={column: f"snis_{name}" for column, name in INDICATORS.items()})
    df["municipality_code"] = raw["id_municipio"].astype(str).str.zfill(7)
    df["snis_reference_year"] = raw["ano"].astype("int64")
    return df[["municipality_code", "snis_reference_year", *GOLD_FEATURES[:-1]]].drop_duplicates(
        ["municipality_code", "snis_reference_year"], keep="last"
    )


def build_sanitation(
    reported: pd.DataFrame, dim: pd.DataFrame, first_year: int, last_year: int, max_carry_years: int
) -> pd.DataFrame:
    grid = pd.MultiIndex.from_product(
        [dim["municipality_code"], range(first_year, last_year + 1)], names=["municipality_code", "year"]
    ).to_frame(index=False)
    grid["year"] = grid["year"].astype("int64")

    df = pd.merge_asof(
        grid.sort_values("year"),
        reported.sort_values("snis_reference_year"),
        left_on="year",
        right_on="snis_reference_year",
        by="municipality_code",
        direction="backward",
        tolerance=max_carry_years,
    )
    df = df.merge(dim[["municipality_code", "municipality_code_6"]], on="municipality_code")
    df["snis_reference_year"] = df["snis_reference_year"].astype("Int64")
    return df[["municipality_code", "municipality_code_6", "year", *GOLD_FEATURES]].sort_values(
        ["municipality_code", "year"], ignore_index=True
    )
