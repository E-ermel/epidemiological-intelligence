"""
Atlas Brasil (Base dos Dados) -> indicadores por município × censo.

O gold usa o censo mais recente (2010) como característica fixa de
cada município: o IDHM só é calculado em anos de censo. Municípios
criados depois de 2010 ficam sem valor.
"""

import pandas as pd

RENAME = {
    "ano": "census_year",
    "id_municipio": "municipality_code",
    "idhm": "idhm",
    "idhm_e": "idhm_education",
    "idhm_l": "idhm_longevity",
    "idhm_r": "idhm_income",
    "indice_gini": "gini",
    "renda_pc": "income_per_capita",
    "expectativa_vida": "life_expectancy",
    "mortalidade_1": "infant_mortality",
    "taxa_agua_encanada": "pct_piped_water",
    "taxa_banheiro_agua_encanada": "pct_bathroom_piped_water",
    "taxa_coleta_lixo": "pct_garbage_collection",
    "taxa_agua_esgoto_inadequados": "pct_inadequate_water_sewage",
}

# Indicadores que vão para o gold (prefixo do censo no nome deixa claro
# que é um retrato de 2010, não um valor do mês).
GOLD_FEATURES = [
    "idhm",
    "idhm_education",
    "idhm_longevity",
    "idhm_income",
    "gini",
    "income_per_capita",
    "life_expectancy",
    "infant_mortality",
    "pct_piped_water",
    "pct_bathroom_piped_water",
    "pct_garbage_collection",
    "pct_inadequate_water_sewage",
    "pct_urban",
]


def build_atlas(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=RENAME)
    df["municipality_code"] = df["municipality_code"].astype(str).str.zfill(7)
    df["municipality_code_6"] = df["municipality_code"].str[:6]

    total = df["populacao_urbana"] + df["populacao_rural"]
    df["pct_urban"] = (df["populacao_urbana"] / total * 100).where(total > 0)

    return df[["municipality_code", "municipality_code_6", "census_year", *GOLD_FEATURES]]


def latest_census(atlas: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por município, do censo mais recente, com prefixo atlas_ nas colunas."""

    latest = atlas[atlas["census_year"] == atlas["census_year"].max()]
    return latest[["municipality_code_6", *GOLD_FEATURES]].rename(
        columns={feature: f"atlas_{feature}" for feature in GOLD_FEATURES}
    )
