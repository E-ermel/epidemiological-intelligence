from fastapi import APIRouter
import pandas as pd

from epidemiological_agent.api.gold_data import load_gold_dataframe
from epidemiological_agent.api.schemas_overview import (
    CaseCurvePoint,
    DiseaseDistributionSlice,
    OverviewMetrics,
    OverviewResponse,
)

router = APIRouter(tags=["overview"])

TREND_WINDOW_MONTHS = 12


def _trend_pct(df: pd.DataFrame, period_end: pd.Timestamp) -> float | None:
    cutoff = period_end - pd.DateOffset(months=TREND_WINDOW_MONTHS)
    prior_cutoff = cutoff - pd.DateOffset(months=TREND_WINDOW_MONTHS)

    current = df.loc[df["reference_date"] > cutoff, "cases"].sum()
    prior = df.loc[
        (df["reference_date"] > prior_cutoff) & (df["reference_date"] <= cutoff),
        "cases",
    ].sum()

    if not prior:
        return None

    return round((current - prior) / prior * 100, 1)


@router.get("/overview", response_model=OverviewResponse)
def get_overview() -> OverviewResponse:
    df = load_gold_dataframe()

    total_cases = float(df["cases"].sum(skipna=True))
    period_start = df["reference_date"].min()
    period_end = df["reference_date"].max()

    case_curve_series = (
        df.groupby(df["reference_date"].dt.to_period("M"))["cases"]
        .sum()
        .reset_index()
    )
    case_curve_series["reference_date"] = case_curve_series[
        "reference_date"
    ].dt.to_timestamp()

    disease_totals = df.groupby("disease")["cases"].sum()

    return OverviewResponse(
        metrics=OverviewMetrics(
            total_cases=int(total_cases),
            total_cases_trend_pct=_trend_pct(df, period_end),
            municipality_count=int(df["municipality"].nunique()),
            disease_count=int(df["disease"].nunique()),
            period_start=period_start.date().isoformat(),
            period_end=period_end.date().isoformat(),
        ),
        case_curve=[
            CaseCurvePoint(
                reference_date=row.reference_date.date().isoformat(),
                cases=int(row.cases),
            )
            for row in case_curve_series.itertuples()
        ],
        disease_distribution=[
            DiseaseDistributionSlice(
                disease=disease,
                cases=int(cases),
                share_of_total_pct=(
                    round(float(cases) / total_cases * 100, 1)
                    if total_cases
                    else 0.0
                ),
            )
            for disease, cases in disease_totals.items()
        ],
    )
