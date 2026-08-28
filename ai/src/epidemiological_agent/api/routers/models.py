import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from epidemiological_agent.api.gold_data import load_gold_dataframe
from epidemiological_agent.api.model_metadata_batch import (
    fetch_model_metadata_for_diseases,
)
from epidemiological_agent.api.schemas_models import (
    ModelMetadataResponse,
    PredictionPoint,
)
from epidemiological_agent.tools.model_tools import get_predictions

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelMetadataResponse])
def get_models() -> list[ModelMetadataResponse]:
    # Diseases come from the Gold table itself, not a hardcoded list --
    # ai/ has no MODEL_CONFIG of its own (that lives in data_science/,
    # a separately deployed service), and this way a disease that shows
    # up in new data doesn't need a code change here to be picked up.
    diseases = load_gold_dataframe()["disease"].unique()

    metadata_by_disease = fetch_model_metadata_for_diseases(diseases)

    return [
        ModelMetadataResponse(**metadata)
        for metadata in metadata_by_disease.values()
        if metadata is not None
        # None means the disease has epidemiological data but no
        # trained model yet.
    ]


@router.get(
    "/models/{disease}/predictions",
    response_model=list[PredictionPoint],
)
def get_model_predictions(
    disease: str,
    municipality: str | None = Query(default=None),
) -> list[PredictionPoint]:
    try:
        df = get_predictions(disease)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No predictions found for disease: {disease}",
        )

    if municipality is not None:
        df = df[df["municipality"].str.upper() == municipality.upper()]

    return [
        PredictionPoint(
            reference_date=pd.Timestamp(row.reference_date).date().isoformat(),
            municipality=row.municipality,
            observed_cases=float(row.cases),
            predicted_cases=float(row.final_prediction),
        )
        for row in df.itertuples()
    ]
