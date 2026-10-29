"""
Arquivos do dashboard PRODES -> desmatamento anual por município.

- Ano: o período PRODES vai de agosto a julho e leva o ano em que
  termina (PRODES 2024 = ago/2023 a jul/2024). Períodos de mais de um
  ano (Caatinga, Mata Atlântica, Pampa e Pantanal têm um bienal
  2014-2016) são divididos igualmente entre os anos que cobrem; o
  acumulado histórico do início da série (1500-2000) fica de fora.
- Município em mais de um bioma: soma dos biomas.
- Zero x nulo: município de um bioma sem polígono no ano tem zero; se
  algum bioma do município ainda não publicou aquele ano (o INPE solta
  Amazônia e Cerrado antes dos outros), o valor fica nulo em vez de um
  total parcial.
"""

import pandas as pd

GOLD_FEATURES = ["deforestation_km2", "deforestation_pct"]


def municipality_codes(loinames: dict) -> dict[int, str]:
    """gid do recorte "mun" -> código IBGE de 7 dígitos."""

    mun = next(loi for loi in loinames["lois"] if loi["name"] == "mun")
    return {item["gid"]: str(item["codibge"]).zfill(7) for item in mun["loinames"] if item.get("codibge")}


def _mun_loi_gid(loinames: dict) -> int:
    return next(loi["gid"] for loi in loinames["lois"] if loi["name"] == "mun")


# Acima disso é o acumulado do início da série, não um incremento.
MAX_PERIOD_YEARS = 4


def period_years(period: dict) -> list[int]:
    """Anos PRODES cobertos pelo período (vazio para o acumulado)."""

    end = period["endDate"]["year"]
    span = end - period["startDate"]["year"]
    if not 1 <= span <= MAX_PERIOD_YEARS:
        return []
    return list(range(end - span + 1, end + 1))


def parse_biome(data: dict, loinames: dict, first_year: int) -> tuple[pd.DataFrame, set[str], set[int]]:
    """
    Retorna (desmatamento por município × ano, municípios do bioma,
    anos publicados).
    """

    codes = municipality_codes(loinames)
    mun_gid = _mun_loi_gid(loinames)

    rows, published = [], set()
    for period in data["periods"]:
        years = period_years(period)
        kept = [year for year in years if year >= first_year]
        if not kept:
            continue
        published.update(kept)
        for feature in period["features"]:
            if feature["loi"] != mun_gid or feature["loiname"] not in codes:
                continue
            area = sum(item["area"] for item in feature["areas"]) / len(years)
            rows.extend(
                {"municipality_code": codes[feature["loiname"]], "year": year, "deforestation_km2": area}
                for year in kept
            )

    df = pd.DataFrame(rows, columns=["municipality_code", "year", "deforestation_km2"])
    return df, set(codes.values()), published


def build_deforestation(biomes: list[tuple[pd.DataFrame, set[str], set[int]]], dim: pd.DataFrame) -> pd.DataFrame:
    years = sorted(set().union(*(published for _, _, published in biomes)))
    grid = pd.MultiIndex.from_product([dim["municipality_code"], years], names=["municipality_code", "year"])

    total = (
        pd.concat([df for df, _, _ in biomes], ignore_index=True)
        .groupby(["municipality_code", "year"])["deforestation_km2"]
        .sum()
        .reindex(grid, fill_value=0.0)
    )

    for _, members, published in biomes:
        missing = [year for year in years if year not in published]
        if missing:
            incomplete = grid.get_level_values("municipality_code").isin(members) & grid.get_level_values("year").isin(
                missing
            )
            total[incomplete] = float("nan")

    df = total.reset_index().merge(dim[["municipality_code", "municipality_code_6", "area_km2"]], on="municipality_code")
    df["deforestation_pct"] = df["deforestation_km2"] / df["area_km2"].where(df["area_km2"] > 0) * 100
    return df[["municipality_code", "municipality_code_6", "year", *GOLD_FEATURES]]
