from fastapi import APIRouter

from epidemiological_agent.api.gold_data import load_gold_dataframe
from epidemiological_agent.api.schemas_studies import StudySummary
from epidemiological_agent.tools.model_tools import get_model_metadata

router = APIRouter(tags=["studies"])


@router.get("/studies", response_model=list[StudySummary])
def get_studies() -> list[StudySummary]:
    df = load_gold_dataframe()

    summaries = []

    for disease, group in df.groupby("disease"):
        try:
            active_version = get_model_metadata(disease)["model_version"]
        except FileNotFoundError:
            # Disease has epidemiological data but no trained model yet.
            active_version = None

        summaries.append(
            StudySummary(
                disease=disease,
                total_cases=int(group["cases"].sum(skipna=True)),
                municipality_count=int(group["municipality"].nunique()),
                active_model_version=active_version,
            )
        )

    return summaries
