import json
import os
import re
import unicodedata
from io import BytesIO
from typing import Any

import pandas as pd
from google.cloud import storage

from epidemiological_agent.config import PROJECT_ID


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
    """
    Convert disease names to the same slug format
    used by the Data Science artifact pipeline.
    """

    normalized = unicodedata.normalize(
        "NFKD",
        disease,
    )

    ascii_name = normalized.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    slug = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        ascii_name,
    )

    return slug.strip("_").lower()


def _get_bucket():
    """
    Return the GCS bucket used by model artifacts.
    """

    client = storage.Client(
        project=PROJECT_ID
    )

    return client.bucket(
        ARTIFACT_BUCKET
    )


def _get_latest_model_info(
    disease: str,
) -> dict[str, Any]:
    """
    Read latest.json and return information about
    the currently active model version.
    """

    bucket = _get_bucket()

    disease_name = _normalize_disease_name(
        disease
    )

    blob_path = (
        f"{MODEL_ARTIFACT_PREFIX.rstrip('/')}/"
        f"{disease_name}/"
        f"latest.json"
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Latest model version not found "
            f"for disease: {disease}"
        )

    content = blob.download_as_text(
        encoding="utf-8"
    )

    return json.loads(content)


def _get_versioned_artifact_path(
    disease: str,
    filename: str,
) -> str:
    """
    Resolve the GCS path of an artifact using
    the active version stored in latest.json.
    """

    latest = _get_latest_model_info(
        disease
    )

    version_path = latest.get("path")

    if not version_path:
        raise ValueError(
            f"Invalid latest.json for disease "
            f"{disease}: missing 'path'."
        )

    return (
        f"{version_path.rstrip('/')}/"
        f"{filename}"
    )


def get_model_metrics(
    disease: str,
) -> dict:

    bucket = _get_bucket()

    blob_path = _get_versioned_artifact_path(
        disease=disease,
        filename="metrics.json",
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Metrics not found for disease: "
            f"{disease}"
        )

    content = blob.download_as_text(
        encoding="utf-8"
    )

    return json.loads(content)


def get_model_metadata(
    disease: str,
) -> dict:
    """
    Read metadata.json for the active model version (disease,
    model_version, run_id, trained_at, model_type, features,
    training_period, test_period, metrics) -- everything
    get_model_metrics() alone doesn't have, since that only reads
    metrics.json.
    """

    bucket = _get_bucket()

    blob_path = _get_versioned_artifact_path(
        disease=disease,
        filename="metadata.json",
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Metadata not found for disease: "
            f"{disease}"
        )

    content = blob.download_as_text(
        encoding="utf-8"
    )

    return json.loads(content)


def get_predictions(
    disease: str,
) -> pd.DataFrame:

    bucket = _get_bucket()

    blob_path = _get_versioned_artifact_path(
        disease=disease,
        filename="predictions.parquet",
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Predictions not found for disease: "
            f"{disease}"
        )

    data = blob.download_as_bytes()

    return pd.read_parquet(
        BytesIO(data)
    )


def get_municipality_metrics(
    disease: str,
) -> pd.DataFrame:

    bucket = _get_bucket()

    blob_path = _get_versioned_artifact_path(
        disease=disease,
        filename="municipality_metrics.parquet",
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Municipality metrics not found "
            f"for disease: {disease}"
        )

    data = blob.download_as_bytes()

    return pd.read_parquet(
        BytesIO(data)
    )