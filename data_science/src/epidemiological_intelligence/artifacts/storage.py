import json
import os
from io import BytesIO
from typing import Any

import pandas as pd
from google.cloud import storage


def get_storage_config() -> tuple[str, str, str]:
    """
    Return the GCP project, artifact bucket and artifact prefix
    used by the modeling pipeline.
    """

    project_id = os.getenv("GCP_PROJECT_ID")

    bucket_name = os.getenv(
        "ARTIFACT_BUCKET",
        "epidemiological-intelligence",
    )

    artifact_prefix = os.getenv(
        "MODEL_ARTIFACT_PREFIX",
        "modeling",
    )

    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID não foi definido."
        )

    return project_id, bucket_name, artifact_prefix


def get_storage_client() -> storage.Client:
    project_id, _, _ = get_storage_config()

    return storage.Client(
        project=project_id
    )


def upload_json(
    *,
    bucket_name: str,
    blob_path: str,
    data: dict[str, Any],
) -> None:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)

    blob = bucket.blob(blob_path)

    content = json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
        default=str,
    )

    blob.upload_from_string(
        content,
        content_type="application/json",
    )


def upload_dataframe(
    *,
    bucket_name: str,
    blob_path: str,
    dataframe: pd.DataFrame,
) -> None:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)

    buffer = BytesIO()

    dataframe.to_parquet(
        buffer,
        index=False,
    )

    buffer.seek(0)

    blob = bucket.blob(blob_path)

    blob.upload_from_file(
        buffer,
        content_type="application/octet-stream",
    )