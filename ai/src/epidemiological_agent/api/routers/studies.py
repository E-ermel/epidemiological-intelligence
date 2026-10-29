import pandas as pd
from fastapi import APIRouter
from google.api_core.exceptions import GoogleAPIError

from epidemiological_agent.tools import alert_queries, gold_queries
from epidemiological_agent.tools.gold_queries import GoldFilters
from epidemiological_agent.api.schemas_studies import StudySummary

router = APIRouter(tags=["studies"])


@router.get("/studies", response_model=list[StudySummary])
def get_studies() -> list[StudySummary]:
    by_disease = gold_queries.cases_by_disease(GoldFilters())

    # Alerta da origem "fechado" (dados completos). Antes da primeira
    # rodada do job a tabela não existe: os cartões saem sem alerta.
    try:
        alerts = alert_queries.alerts_by_disease("fechado")
    except GoogleAPIError:
        alerts = pd.DataFrame(columns=["disease", "state_alerts", "max_probability"])
    by_disease = by_disease.merge(alerts, on="disease", how="left")

    return [
        StudySummary(
            disease=row.disease,
            total_cases=int(row.cases),
            municipality_count=int(row.municipality_count),
            states_in_alert=None if pd.isna(row.state_alerts) else int(row.state_alerts),
            max_alert_probability=None if pd.isna(row.max_probability) else float(row.max_probability),
        )
        for row in by_disease.itertuples()
    ]
