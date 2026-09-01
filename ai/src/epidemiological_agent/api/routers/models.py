import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from google.api_core.exceptions import GoogleAPICallError

from epidemiological_agent.api.gold_data import load_gold_dataframe
from epidemiological_agent.api.model_metadata_batch import (
    fetch_model_metadata_for_diseases,
)
from epidemiological_agent.api.retrain_job import (
    get_execution_status,
    summarize_execution_status,
    trigger_retrain,
)
from epidemiological_agent.api.schemas_models import (
    ModelMetadataResponse,
    PredictionPoint,
    RetrainExecutionStatus,
    RetrainResponse,
)
from epidemiological_agent.tools.model_tools import (
    get_predictions,
    invalidate_model_metadata_cache,
)

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


@router.post("/models/{disease}/retrain", response_model=RetrainResponse)
def retrain_model(disease: str) -> RetrainResponse:
    known_diseases = set(load_gold_dataframe()["disease"].unique())

    if disease not in known_diseases:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown disease: {disease}",
        )

    try:
        execution_name = trigger_retrain(disease)
    except GoogleAPICallError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to start retrain job: {error}",
        )

    return RetrainResponse(status="started", execution_name=execution_name)


@router.get("/models/retrain/status", response_model=RetrainExecutionStatus)
def get_retrain_status(execution: str = Query(...)) -> RetrainExecutionStatus:
    """Polled by the frontend (executionName from the POST .../retrain
    response) to know when a retrain actually finishes, not just when
    it was accepted."""

    try:
        execution_obj = get_execution_status(execution)
    except GoogleAPICallError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch execution status: {error}",
        )

    status = summarize_execution_status(execution_obj)

    if status == "succeeded":
        # Which disease (or all of them) isn't tracked here -- clearing
        # the whole cache is a handful of extra GCS reads on the next
        # /models or /studies call, not worth parsing out of the
        # execution's DISEASE_FILTER override for.
        invalidate_model_metadata_cache()

    return RetrainExecutionStatus(
        status=status,
        log_uri=execution_obj.log_uri or None,
        start_time=(
            execution_obj.start_time.isoformat()
            if execution_obj.start_time is not None
            else None
        ),
        completion_time=(
            execution_obj.completion_time.isoformat()
            if execution_obj.completion_time is not None
            else None
        ),
    )


@router.post("/models/retrain", response_model=RetrainResponse)
def retrain_all_models() -> RetrainResponse:
    """Bulk equivalent of retrain_model -- one job execution, every disease."""

    try:
        execution_name = trigger_retrain()
    except GoogleAPICallError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to start retrain job: {error}",
        )

    return RetrainResponse(status="started", execution_name=execution_name)
