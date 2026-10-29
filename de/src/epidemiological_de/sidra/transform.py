"""
Respostas do SIDRA -> população por município × ano.

- Estimativas anuais e o Censo 2022 (o censo vale onde existir).
- Anos sem número publicado entre dois anos com número (2023, entre o
  censo e a estimativa de 2024) são interpolados linearmente.
- Antes do primeiro número de um município (municípios novos, como Boa
  Esperança do Norte/MT, de 2024) fica sem população: não se inventa
  população para um município que não existia.

Atenção: as estimativas até 2021 partiam do Censo 2010 e superestimavam
a população (Brasil: 213 milhões em 2021 contra 203 milhões no Censo
2022). A coluna population_source deixa a quebra visível.
"""

import pandas as pd

SILVER_COLUMNS = [
    "municipality_code",
    "municipality_code_6",
    "year",
    "population",
    "population_source",
    "area_km2",
    "population_density",
]

ESTIMATE = "estimativa"
CENSUS = "censo"
INTERPOLATED = "interpolado"


def parse_sidra(rows: list[dict], source: str) -> pd.DataFrame:
    """
    Formato da API de valores do SIDRA: a primeira linha é o cabeçalho;
    D1C = código do município (7 dígitos), D3C = ano, V = valor. Valor
    não numérico ("...", "-", "X") é ausência de dado.
    """

    df = pd.DataFrame(rows[1:])
    return pd.DataFrame(
        {
            "municipality_code": df["D1C"].astype(str),
            "year": df["D3C"].astype(int),
            "population": pd.to_numeric(df["V"], errors="coerce"),
            "population_source": source,
        }
    ).dropna(subset=["population"])


def build_population(estimates: pd.DataFrame, census: pd.DataFrame, dim: pd.DataFrame) -> pd.DataFrame:
    """Série anual completa por município da dim, com densidade (hab/km²)."""

    # Censo depois das estimativas: no mesmo ano, vale o censo.
    published = (
        pd.concat([estimates, census], ignore_index=True)
        .drop_duplicates(["municipality_code", "year"], keep="last")
    )

    years = range(int(published["year"].min()), int(published["year"].max()) + 1)
    grid = pd.MultiIndex.from_product([dim["municipality_code"], years], names=["municipality_code", "year"])
    series = published.set_index(["municipality_code", "year"]).reindex(grid).reset_index()

    # Só entre dois números publicados (limit_area="inside").
    series["population"] = series.groupby("municipality_code")["population"].transform(
        lambda s: s.interpolate(limit_area="inside")
    )
    filled = series["population_source"].isna() & series["population"].notna()
    series.loc[filled, "population_source"] = INTERPOLATED
    series = series.dropna(subset=["population"])

    series = series.merge(dim[["municipality_code", "municipality_code_6", "area_km2"]], on="municipality_code")
    series["population"] = series["population"].round().astype("int64")
    series["population_density"] = series["population"] / series["area_km2"]

    return series[SILVER_COLUMNS].sort_values(["municipality_code", "year"]).reset_index(drop=True)
