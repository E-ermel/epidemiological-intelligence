"""
Do gold aos painéis do alerta: origens de cada doença, séries municipais
elegíveis, painel por UF e por município (com clima sem buracos) e canal
endêmico (limite de surto) de cada mês, inclusive dos meses previstos.
"""

import warnings

import numpy as np
import pandas as pd

from epidemiological_intelligence.alert import config


# ---------------------------------------------------------------------
# Origens
# ---------------------------------------------------------------------


def _origin_months(df: pd.DataFrame, source: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """(fechada, provisória) pela regra da completude, a partir dos casos em `df`."""

    monthly = df.groupby("ds").agg(total=("cases", "sum"), provisional=("is_provisional", "any"))
    monthly = monthly[monthly["total"] > 0].sort_index()
    last_with_data = monthly.index[-1]

    provisional = last_with_data
    if len(monthly) > 1 and monthly["total"].iloc[-1] < config.PARTIAL_MONTH_SHARE * monthly["total"].iloc[-2]:
        provisional = monthly.index[-2]  # último mês ainda em andamento

    if source == "SINAN":
        closed = last_with_data - pd.DateOffset(months=config.SINAN_CLOSED_LAG_MONTHS)
    else:
        settled = monthly.index[~monthly["provisional"]]
        closed = settled.max() if len(settled) else monthly.index[0]
    return min(closed, provisional), provisional


def source_origins(cases: pd.DataFrame) -> pd.DataFrame:
    """Origem fechada e provisória de cada fonte (SIH, SINAN)."""

    rows = []
    for source, df in cases.groupby("source", observed=True):
        closed, provisional = _origin_months(df, str(source))
        rows += [
            {"source": source, "origin_type": "fechado", "origin": closed},
            {"source": source, "origin_type": "provisorio", "origin": provisional},
        ]
    return pd.DataFrame(rows)


def disease_origins(cases: pd.DataFrame, override: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    Origem de cada doença × tipo; `override` força a mesma data para todas (validação).

    Nas fontes de ORIGIN_BY_DISEASE_SOURCES (SINAN: um arquivo por agravo,
    atualizado em datas diferentes) a origem sai dos casos da própria
    doença. Nas demais (SIH: os mesmos arquivos mensais para todas), sai
    da fonte inteira -- por doença, um mês sem internação de Oropouche
    pareceria um mês sem dado.
    """

    diseases = cases[["disease", "source"]].drop_duplicates().astype(str)
    origins = diseases.merge(source_origins(cases).astype({"source": str}), on="source")

    by_disease = cases[cases["source"].astype(str).isin(config.ORIGIN_BY_DISEASE_SOURCES)]
    for (disease, source), df in by_disease.groupby(["disease", "source"], observed=True):
        closed, provisional = _origin_months(df, str(source))
        row = origins["disease"] == str(disease)
        origins.loc[row & (origins["origin_type"] == "fechado"), "origin"] = closed
        origins.loc[row & (origins["origin_type"] == "provisorio"), "origin"] = provisional

    if override is not None:
        origins["origin"] = override
    return origins.reset_index(drop=True)


# ---------------------------------------------------------------------
# Séries municipais elegíveis
# ---------------------------------------------------------------------


def eligible_municipal_series(cases: pd.DataFrame, origins: pd.DataFrame) -> pd.DataFrame:
    """Doença × município com média >= MIN_MEAN_CASES_MUNICIPIO nos 60 meses até a origem fechada."""

    closed = origins[origins["origin_type"] == "fechado"].set_index("disease")["origin"]
    disease = cases["disease"].astype(str)
    end = disease.map(closed)
    start = end - pd.DateOffset(months=config.ELIGIBILITY_MONTHS - 1)
    window = cases[(cases["ds"] >= start) & (cases["ds"] <= end)]
    mean = window.groupby(["disease", "municipality_code"], observed=True)["cases"].mean()
    return mean[mean >= config.MIN_MEAN_CASES_MUNICIPIO].reset_index()[["disease", "municipality_code"]]


# ---------------------------------------------------------------------
# Painéis
# ---------------------------------------------------------------------


def fill_climate(context: pd.DataFrame) -> pd.DataFrame:
    """Buraco de clima: média do mesmo mês no município, depois da UF no mês, depois do mês no país."""

    context = context.copy()
    calendar_month = context["ds"].dt.month
    for column in config.CLIMATE:
        by_municipality_month = context.groupby(["municipality_code", calendar_month])[column].transform("mean")
        by_state_date = context.groupby(["state", "ds"])[column].transform("mean")
        overall_month = context.groupby(calendar_month)[column].transform("mean")
        context[column] = context[column].fillna(by_municipality_month).fillna(by_state_date).fillna(overall_month)
    return context


def _weighted_mean(df: pd.DataFrame, columns: list[str], keys: list[str]) -> pd.DataFrame:
    """Média ponderada pela população, ignorando nulos coluna a coluna."""

    out = {}
    groups = [df[k] for k in keys]
    for column in columns:
        weight = df["population"].where(df[column].notna(), 0.0)
        out[column] = (df[column].fillna(0) * weight).groupby(groups).sum() / weight.groupby(groups).sum().replace(
            0, np.nan
        )
    return pd.DataFrame(out).reset_index()


def _complete_grid(panel: pd.DataFrame, keys: list[str], last_month: pd.Timestamp) -> pd.DataFrame:
    """Grade mensal completa por série, de jan/2015 (ou o início) até last_month (y nulo no futuro)."""

    months = pd.date_range(panel["ds"].min(), last_month, freq="MS")
    series = panel[keys].drop_duplicates()
    grid = series.loc[series.index.repeat(len(months))].reset_index(drop=True)
    grid["ds"] = np.tile(months, len(series))
    return grid.merge(panel, on=[*keys, "ds"], how="left")


def build_panel(
    level: str,
    cases: pd.DataFrame,
    context: pd.DataFrame,
    eligible: pd.DataFrame,
    last_month: pd.Timestamp,
) -> pd.DataFrame:
    """
    Painel do nível com series_id, y (casos), is_provisional, população,
    clima e canal endêmico, de 2015 até last_month (meses previstos com
    y nulo).
    """

    context = fill_climate(context[context["population"].notna()])

    if level == "municipio":
        key = pd.MultiIndex.from_arrays([cases["disease"].astype(str), cases["municipality_code"].astype(str)])
        df = cases[key.isin(pd.MultiIndex.from_frame(eligible.astype(str)))]
        df = df.astype({"disease": str, "source": str, "municipality_code": str, "state": str})
        df = df.merge(context.drop(columns="state"), on=["municipality_code", "ds"])
        keys = ["disease", "source", "state", "municipality_code"]
        df = df.rename(columns={"cases": "y"})[[*keys, "ds", "y", "is_provisional", "population", *config.CLIMATE]]
    else:
        by_state = cases.groupby(["disease", "source", "state", "ds"], observed=True).agg(
            y=("cases", "sum"), is_provisional=("is_provisional", "any")
        ).reset_index().astype({"disease": str, "source": str, "state": str})
        state_context = _weighted_mean(context, config.CLIMATE, ["state", "ds"]).merge(
            context.groupby(["state", "ds"], as_index=False)["population"].sum(), on=["state", "ds"]
        )
        keys = ["disease", "source", "state"]
        df = by_state.merge(state_context.astype({"state": str}), on=["state", "ds"])

    df = _complete_grid(df, keys, last_month)
    df["series_id"] = df["disease"] + "|" + df[keys[-1]].astype(str)
    df = df.sort_values(["series_id", "ds"]).reset_index(drop=True)
    return endemic_channel(df, level)


def endemic_channel(panel: pd.DataFrame, level: str) -> pd.DataFrame:
    """
    Limite de surto de cada mês: média + 1,96 desvio-padrão do mesmo mês
    nos 5 anos anteriores (nulo sem 5 anos), pulando os anos de
    CHANNEL_EXCLUDED_YEARS da fonte da série. Vale também para meses
    ainda sem casos (os previstos): só usa anos passados.
    """

    df = panel.copy()
    excluded_by_source = config.CHANNEL_EXCLUDED_YEARS
    excluded = pd.Series(False, index=df.index)
    if "source" in df:
        for source, years in excluded_by_source.items():
            excluded |= (df["source"] == source) & df["ds"].dt.year.isin(years)

    # Agrupado por mês do calendário (grade mensal completa), shift(k) é o
    # mesmo mês k anos antes; anos excluídos viram NaN e ficam os
    # CHANNEL_YEARS valores mais recentes que sobram.
    depth = config.CHANNEL_YEARS + max((len(y) for y in excluded_by_source.values()), default=0)
    grouped = df["y"].where(~excluded).groupby([df["series_id"], df["ds"].dt.month])
    past = np.column_stack([grouped.shift(k).to_numpy(dtype=float) for k in range(1, depth + 1)])
    valid = ~np.isnan(past)
    keep = valid & (np.cumsum(valid, axis=1) <= config.CHANNEL_YEARS)
    kept = np.where(keep, past, np.nan)
    enough = keep.sum(axis=1) == config.CHANNEL_YEARS
    with warnings.catch_warnings():  # séries sem 5 anos: fatia vazia, vira NaN
        warnings.simplefilter("ignore", RuntimeWarning)
        df["channel_mean"] = np.where(enough, np.nanmean(kept, axis=1), np.nan)
        df["channel_sd"] = np.where(enough, np.nanstd(kept, axis=1, ddof=1), np.nan)
    df["threshold"] = df["channel_mean"] + config.CHANNEL_Z * df["channel_sd"]
    df["min_cases"] = config.MIN_CASES[level]
    return df
