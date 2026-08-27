import json
import os
from io import BytesIO

import pandas as pd
from google.cloud import storage

from epidemiological_agent.config import (PROJECT_ID)

ARTIFACT_BUCKET = os.getenv(
    "ARTIFACT_BUCKET",
    "epidemiological-intelligence",
)

MODEL_ARTIFACT_PREFIX = os.getenv(
    "MODEL_ARTIFACT_PREFIX",
    "modeling",
)

def _normalize_disease_name(
    disease: str,
) -> str:
    
    return(
        disease
        .lower()
        .replace(" ", "_")
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
    )

def get_model_metrics(
    disease: str,
) -> dict:
    
    client = storage.Client(
        project=PROJECT_ID
    )
    
    bucket = client.bucket(
        ARTIFACT_BUCKET
    )
    disease_name = (
        _normalize_disease_name(
            disease
        )
    )

    blob_path = (
            f"{MODEL_ARTIFACT_PREFIX}/"
            f"{disease_name}/"
            f"metrics.json"
        )

    blob = bucket.blob(
            blob_path
        )

    if not blob.exists():
            raise FileNotFoundError(
                f"Metrics not found for disease: {disease}"
            )

    content = blob.download_as_text(
            encoding="utf-8"
        )

    return json.loads(content)

def get_predictions(
    disease: str,
) -> pd.DataFrame:
    
    client = storage.Client(
        project=PROJECT_ID
    )

    bucket = client.bucket(
        ARTIFACT_BUCKET
    )

    disease_name = _normalize_disease_name(
        disease
    )

    blob_path = (
        f"{MODEL_ARTIFACT_PREFIX}/"
        f"{disease_name}/"
        f"predictions.parquet"
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Predictions not found for disease: {disease}"
        )

    data = blob.download_as_bytes()

    return pd.read_parquet(
        BytesIO(data)
    )
    
def get_municipality_metrics(
    disease: str,
) -> pd.DataFrame:

    client = storage.Client(
        project=PROJECT_ID
    )

    bucket = client.bucket(
        ARTIFACT_BUCKET
    )

    disease_name = _normalize_disease_name(
        disease
    )

    blob_path = (
        f"{MODEL_ARTIFACT_PREFIX}/"
        f"{disease_name}/"
        f"municipality_metrics.parquet"
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Municipality metrics not found for disease: {disease}"
        )

    data = blob.download_as_bytes()

    return pd.read_parquet(
        BytesIO(data)
    )