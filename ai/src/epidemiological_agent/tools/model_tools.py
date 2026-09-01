import json
import os
import re
import time
import unicodedata
from functools import lru_cache
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


@lru_cache(maxsize=1)
def _get_storage_client() -> storage.Client:
    # Constructing a client does credential discovery on every call
    # (measured ~1s+ each); storage.Client is documented safe to reuse.
    return storage.Client(project=PROJECT_ID)


def _get_bucket():
    """
    Return the GCS bucket used by model artifacts.
    """

    return _get_storage_client().bucket(
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


_METADATA_CACHE_TTL_SECONDS = 300
_metadata_cache: dict[str, tuple[float, dict | None]] = {}


def get_model_metadata(
    disease: str,
) -> dict:
    """
    Read metadata.json for the active model version (disease,
    model_version, run_id, trained_at, model_type, features,
    training_period, test_period, metrics) -- everything
    get_model_metrics() alone doesn't have, since that only reads
    metrics.json.

    Cached per disease (including the FileNotFoundError case, so
    repeatedly asking about an untrained disease doesn't repeatedly
    round-trip GCS to find out) -- /models and /studies call this once
    per disease every request, and each call is a real GCS round trip
    (blob.exists() + download), not a local lookup.
    """

    cached = _metadata_cache.get(disease)

    if cached is not None:
        cached_at, cached_value = cached

        if time.time() - cached_at < _METADATA_CACHE_TTL_SECONDS:
            if cached_value is None:
                raise FileNotFoundError(
                    f"Metadata not found for disease: {disease}"
                )
            return cached_value

    bucket = _get_bucket()

    blob_path = _get_versioned_artifact_path(
        disease=disease,
        filename="metadata.json",
    )

    blob = bucket.blob(
        blob_path
    )

    if not blob.exists():
        _metadata_cache[disease] = (time.time(), None)
        raise FileNotFoundError(
            f"Metadata not found for disease: "
            f"{disease}"
        )

    content = blob.download_as_text(
        encoding="utf-8"
    )

    metadata = json.loads(content)
    _metadata_cache[disease] = (time.time(), metadata)

    return metadata


def invalidate_model_metadata_cache(disease: str | None = None) -> None:
    """
    Drops cached get_model_metadata() results so the next call re-reads
    GCS. Called when a retrain execution finishes (see GET
    /models/retrain/status) -- otherwise the 5-minute TTL above keeps
    serving a "no model yet" result cached before the retrain, even
    though there's now a fresh metadata.json in GCS.
    """

    if disease is None:
        _metadata_cache.clear()
    else:
        _metadata_cache.pop(disease, None)


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