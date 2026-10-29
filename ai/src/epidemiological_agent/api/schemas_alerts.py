from epidemiological_agent.api.schemas_base import CamelModel


class AlertRecord(CamelModel):
    origin_type: str
    origin_month: str
    level: str
    disease: str
    source: str
    state: str
    municipality_code: str | None
    municipality_name: str | None
    target_month: str
    horizon: int
    threshold: float
    cases_p10: float
    cases_p50: float
    cases_p90: float
    probability: float
    cutoff: float
    alert: bool
    observed_cases: float | None
    target_provisional: bool | None


class AlertStateSummary(CamelModel):
    state: str
    name: str
    max_probability: float | None
    state_alerts: int
    municipality_alerts: int


class AlertLevelMetrics(CamelModel):
    precision: float
    recall: float
    f1: float
    auc_pr: float
    auc_roc: float
    brier: float
    test_predictions: int
    outbreak_pct: float


class AlertOrigin(CamelModel):
    origin_type: str
    disease: str
    origin_month: str


class AlertModelInfo(CamelModel):
    run_id: str
    model_version: str
    model_name: str
    covariates: list[str]
    horizons: list[int]
    cutoffs: dict[str, float]
    test_metrics: dict[str, AlertLevelMetrics]
    origins: list[AlertOrigin]
