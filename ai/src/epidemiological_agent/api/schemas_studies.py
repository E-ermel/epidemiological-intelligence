from epidemiological_agent.api.schemas_base import CamelModel


class StudySummary(CamelModel):
    disease: str
    total_cases: int
    municipality_count: int
    # Alerta de surtos (origem "fechado"): UFs em alerta em algum dos 3
    # meses à frente e a maior probabilidade de surto entre elas. None
    # quando o job do alerta ainda não rodou ou a doença não é alertada
    # (Oropouche).
    states_in_alert: int | None
    max_alert_probability: float | None
