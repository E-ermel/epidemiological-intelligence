from fastapi import APIRouter

from epidemiological_agent.tools import gold_queries
from epidemiological_agent.tools.gold_queries import GoldFilters
from epidemiological_agent.api.model_metadata_batch import (
    fetch_model_metadata_for_diseases,
)
from epidemiological_agent.api.schemas_studies import StudySummary

router = APIRouter(tags=["studies"])


@router.get("/studies", response_model=list[StudySummary])
def get_studies() -> list[StudySummary]:
    by_disease = gold_queries.cases_by_disease(GoldFilters())

    metadata_by_disease = fetch_model_metadata_for_diseases(by_disease["disease"].tolist())

    return [
        StudySummary(
            disease=row.disease,
            total_cases=int(row.cases),
            municipality_count=int(row.municipality_count),
            active_model_version=(
                metadata_by_disease[row.disease]["model_version"]
                if metadata_by_disease.get(row.disease) is not None
                else None
            ),
        )
        for row in by_disease.itertuples()
    ]
