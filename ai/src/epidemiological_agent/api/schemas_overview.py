from epidemiological_agent.api.schemas_base import CamelModel


class OverviewMetrics(CamelModel):
    total_cases: int
    total_cases_trend_pct: float | None
    municipality_count: int
    disease_count: int
    period_start: str
    period_end: str


class CaseCurvePoint(CamelModel):
    reference_date: str
    cases: int


class DiseaseDistributionSlice(CamelModel):
    disease: str
    cases: int
    share_of_total_pct: float


class OverviewResponse(CamelModel):
    metrics: OverviewMetrics
    case_curve: list[CaseCurvePoint]
    disease_distribution: list[DiseaseDistributionSlice]
