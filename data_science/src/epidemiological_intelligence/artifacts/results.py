import json
import os
from io import BytesIO

import pandas as pd
from google.cloud import storage


def _get_gcs_config():
    bucket_name = os.getenv(
        "ARTIFACT_BUCKET",
        "epidemiological-intelligence",
    )

    prefix = os.getenv(
        "MODEL_ARTIFACT_PREFIX",
        "modeling",
    )

    project_id = os.getenv(
        "GCP_PROJECT_ID"
    )

    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID não foi definido."
        )

    return project_id, bucket_name, prefix


def _normalize_disease_name(
    disease: str,
) -> str:

    return (
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


def save_metrics(
    disease: str,
    metrics: dict,
):

    project_id, bucket_name, prefix = (
        _get_gcs_config()
    )

    client = storage.Client(
        project=project_id
    )

    bucket = client.bucket(
        bucket_name
    )

    disease_name = (
        _normalize_disease_name(
            disease
        )
    )

    blob_path = (
        f"{prefix}/"
        f"{disease_name}/"
        f"metrics.json"
    )

    blob = bucket.blob(
        blob_path
    )

    json_content = json.dumps(
        metrics,
        indent=4,
        ensure_ascii=False,
    )

    blob.upload_from_string(
        json_content,
        content_type="application/json",
    )

    print(
        f"Métricas salvas: "
        f"gs://{bucket_name}/{blob_path}"
    )


def save_predictions(
    disease: str,
    predictions: pd.DataFrame,
):

    project_id, bucket_name, prefix = (
        _get_gcs_config()
    )

    client = storage.Client(
        project=project_id
    )

    bucket = client.bucket(
        bucket_name
    )

    disease_name = (
        _normalize_disease_name(
            disease
        )
    )

    blob_path = (
        f"{prefix}/"
        f"{disease_name}/"
        f"predictions.parquet"
    )

    buffer = BytesIO()

    predictions.to_parquet(
        buffer,
        index=False,
    )

    buffer.seek(0)

    blob = bucket.blob(
        blob_path
    )

    blob.upload_from_file(
        buffer,
        content_type=(
            "application/octet-stream"
        ),
    )

    print(
        f"Predições salvas: "
        f"gs://{bucket_name}/{blob_path}"
    )


def save_municipality_metrics(
    disease: str,
    municipality_metrics: pd.DataFrame,
):

    project_id, bucket_name, prefix = (
        _get_gcs_config()
    )

    client = storage.Client(
        project=project_id
    )

    bucket = client.bucket(
        bucket_name
    )

    disease_name = (
        _normalize_disease_name(
            disease
        )
    )

    blob_path = (
        f"{prefix}/"
        f"{disease_name}/"
        f"municipality_metrics.parquet"
    )

    buffer = BytesIO()

    municipality_metrics.to_parquet(
        buffer,
        index=False,
    )

    buffer.seek(0)

    blob = bucket.blob(
        blob_path
    )

    blob.upload_from_file(
        buffer,
        content_type=(
            "application/octet-stream"
        ),
    )

    print(
        f"Métricas municipais salvas: "
        f"gs://{bucket_name}/{blob_path}"
    )