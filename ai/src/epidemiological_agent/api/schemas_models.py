from pydantic import BaseModel

from epidemiological_agent.api.schemas_base import CamelModel


class ModelMetrics(BaseModel):
    mae: float
    rmse: float
    r2: float
    wape_pct: float


class ModelComparison(BaseModel):
    base: ModelMetrics
    final: ModelMetrics
    mae_improvement_pct: float
    rmse_improvement_pct: float


class ModelPeriod(BaseModel):
    start: str
    end: str


class ModelMetadataResponse(BaseModel):
    """
    Mirrors metadata.json (build_model_metadata() in
    data_science/.../artifacts/metadata.py) field-for-field, snake_case
    and all -- it's a pass-through of the real artifact, not a new
    shape invented for the UI, and frontend/types/model.ts already
    expects these exact field names.
    """

    disease: str
    model_version: str
    run_id: str
    trained_at: str
    model_type: str
    features: list[str]
    training_period: ModelPeriod
    test_period: ModelPeriod
    metrics: ModelComparison


class PredictionPoint(CamelModel):
    """New UI-facing shape (not a GCS mirror) -- camelCase."""

    reference_date: str
    municipality: str
    observed_cases: float
    predicted_cases: float


class RetrainResponse(CamelModel):
    status: str
    execution_name: str


class RetrainExecutionStatus(CamelModel):
    """Polled by the frontend via GET /models/retrain/status while a
    retrain is running, so the button can stay disabled until there's a
    real result instead of just until the trigger call returns."""

    status: str  # "running" | "succeeded" | "failed"
    log_uri: str | None = None
    start_time: str | None = None
    completion_time: str | None = None
