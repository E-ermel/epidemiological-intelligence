from typing import Any

import pandas as pd

from epidemiological_intelligence.artifacts.storage import (
    get_storage_config,
    upload_dataframe,
    upload_json,
)

from epidemiological_intelligence.artifacts.versioning import (
    disease_to_slug,
)


def _build_version_path(
    *,
    disease: str,
    version: str,
    filename: str,
) -> str:
    """
    Build the GCS object path for a versioned model artifact.

    Example:
        modeling/leptospirose/v1/metrics.json
    """

    _, _, artifact_prefix = get_storage_config()

    disease_slug = disease_to_slug(disease)

    return (
        f"{artifact_prefix.rstrip('/')}/"
        f"{disease_slug}/"
        f"{version}/"
        f"{filename}"
    )


def save_metrics(
    *,
    disease: str,
    version: str,
    metrics: dict[str, Any],
) -> None:

    _, bucket_name, _ = get_storage_config()

    blob_path = _build_version_path(
        disease=disease,
        version=version,
        filename="metrics.json",
    )

    upload_json(
        bucket_name=bucket_name,
        blob_path=blob_path,
        data=metrics,
    )

    print(
        f"Métricas salvas: "
        f"gs://{bucket_name}/{blob_path}"
    )


def save_predictions(
    *,
    disease: str,
    version: str,
    predictions: pd.DataFrame,
) -> None:

    _, bucket_name, _ = get_storage_config()

    blob_path = _build_version_path(
        disease=disease,
        version=version,
        filename="predictions.parquet",
    )

    upload_dataframe(
        bucket_name=bucket_name,
        blob_path=blob_path,
        dataframe=predictions,
    )

    print(
        f"Predições salvas: "
        f"gs://{bucket_name}/{blob_path}"
    )


def save_municipality_metrics(
    *,
    disease: str,
    version: str,
    municipality_metrics: pd.DataFrame,
) -> None:

    _, bucket_name, _ = get_storage_config()

    blob_path = _build_version_path(
        disease=disease,
        version=version,
        filename="municipality_metrics.parquet",
    )

    upload_dataframe(
        bucket_name=bucket_name,
        blob_path=blob_path,
        dataframe=municipality_metrics,
    )

    print(
        f"Métricas municipais salvas: "
        f"gs://{bucket_name}/{blob_path}"
    )


def save_metadata(
    *,
    disease: str,
    version: str,
    metadata: dict[str, Any],
) -> None:

    _, bucket_name, _ = get_storage_config()

    blob_path = _build_version_path(
        disease=disease,
        version=version,
        filename="metadata.json",
    )

    upload_json(
        bucket_name=bucket_name,
        blob_path=blob_path,
        data=metadata,
    )

    print(
        f"Metadata salva: "
        f"gs://{bucket_name}/{blob_path}"
    )
def save_latest_pointer(
    *,
    disease: str,
    version: str,
    metadata: dict[str, Any],
) -> None:
    """
    Update the pointer to the latest successfully published model version.
    """

    _, bucket_name, artifact_prefix = (
        get_storage_config()
    )

    disease_slug = disease_to_slug(disease)

    blob_path = (
        f"{artifact_prefix.rstrip('/')}/"
        f"{disease_slug}/"
        f"latest.json"
    )

    latest_data = {
        "disease": disease,
        "version": version,
        "run_id": metadata["run_id"],
        "trained_at": metadata["trained_at"],
        "path": (
            f"{artifact_prefix.rstrip('/')}/"
            f"{disease_slug}/"
            f"{version}"
        ),
    }

    upload_json(
        bucket_name=bucket_name,
        blob_path=blob_path,
        data=latest_data,
    )

    print(
        f"Latest atualizado: "
        f"gs://{bucket_name}/{blob_path}"
    )