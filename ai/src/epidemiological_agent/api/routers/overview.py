from fastapi import APIRouter, Query
import pandas as pd

from epidemiological_agent.tools import gold_queries
from epidemiological_agent.tools.gold_queries import GoldFilters
from epidemiological_agent.api.schemas_overview import (
    CaseCurvePoint,
    DiseaseDistributionSlice,
    OverviewMetrics,
    OverviewResponse,
)

router = APIRouter(tags=["overview"])

TREND_WINDOW_MONTHS = 12


def _trend_pct(monthly: pd.DataFrame, period_end: pd.Timestamp) -> float | None:
    cutoff = period_end - pd.DateOffset(months=TREND_WINDOW_MONTHS)
    prior_cutoff = cutoff - pd.DateOffset(months=TREND_WINDOW_MONTHS)

    current = monthly.loc[monthly["reference_date"] > cutoff, "cases"].sum()
    prior = monthly.loc[
        (monthly["reference_date"] > prior_cutoff) & (monthly["reference_date"] <= cutoff),
        "cases",
    ].sum()

    if not prior:
        return None

    return round((current - prior) / prior * 100, 1)


def _empty_response(start_date: str | None, end_date: str | None) -> OverviewResponse:
    return OverviewResponse(
        metrics=OverviewMetrics(
            total_cases=0,
            total_cases_trend_pct=None,
            municipality_count=0,
            disease_count=0,
            period_start=start_date or "",
            period_end=end_date or "",
        ),
        case_curve=[],
        disease_distribution=[],
    )


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    disease: list[str] = Query(default=[]),
    state: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> OverviewResponse:
    filters = GoldFilters(diseases=tuple(disease), state=state, start_date=start_date, end_date=end_date)

    monthly = gold_queries.monthly_cases(filters)

    if monthly.empty:
        return _empty_response(start_date, end_date)

    by_disease = gold_queries.cases_by_disease(filters)
    total_cases = float(monthly["cases"].sum())
    period_start = monthly["reference_date"].min()
    period_end = monthly["reference_date"].max()

    return OverviewResponse(
        metrics=OverviewMetrics(
            total_cases=int(total_cases),
            total_cases_trend_pct=_trend_pct(monthly, period_end),
            municipality_count=gold_queries.municipality_count(filters),
            disease_count=len(by_disease),
            period_start=period_start.date().isoformat(),
            period_end=period_end.date().isoformat(),
        ),
        case_curve=[
            CaseCurvePoint(
                reference_date=row.reference_date.date().isoformat(),
                cases=int(row.cases),
            )
            for row in monthly.itertuples()
        ],
        disease_distribution=[
            DiseaseDistributionSlice(
                disease=row.disease,
                cases=int(row.cases),
                share_of_total_pct=(
                    round(float(row.cases) / total_cases * 100, 1)
                    if total_cases
                    else 0.0
                ),
            )
            for row in by_disease.itertuples()
        ],
    )
