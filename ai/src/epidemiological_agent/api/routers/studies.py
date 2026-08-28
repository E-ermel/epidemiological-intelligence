from fastapi import APIRouter

from epidemiological_agent.api.gold_data import load_gold_dataframe
from epidemiological_agent.api.model_metadata_batch import (
    fetch_model_metadata_for_diseases,
)
from epidemiological_agent.api.schemas_studies import StudySummary

router = APIRouter(tags=["studies"])


@router.get("/studies", response_model=list[StudySummary])
def get_studies() -> list[StudySummary]:
    df = load_gold_dataframe()
    groups = dict(list(df.groupby("disease")))

    metadata_by_disease = fetch_model_metadata_for_diseases(list(groups.keys()))

    return [
        StudySummary(
            disease=disease,
            total_cases=int(group["cases"].sum(skipna=True)),
            municipality_count=int(group["municipality"].nunique()),
            active_model_version=(
                metadata_by_disease[disease]["model_version"]
                if metadata_by_disease.get(disease) is not None
                else None
            ),
        )
        for disease, group in groups.items()
    ]
