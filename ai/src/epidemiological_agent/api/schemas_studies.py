from epidemiological_agent.api.schemas_base import CamelModel


class StudySummary(CamelModel):
    disease: str
    total_cases: int
    municipality_count: int
    active_model_version: str | None
