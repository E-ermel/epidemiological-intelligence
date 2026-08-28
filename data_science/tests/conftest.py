import os
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))

os.environ.setdefault("GCP_PROJECT_ID", "test-project")

import pandas as pd
import pytest

import epidemiological_intelligence.artifacts.storage as storage_module


class _ListedBlob:
    """Minimal stand-in for the objects google.cloud.storage.Client.list_blobs yields."""

    def __init__(self, name):
        self.name = name


class _FakeBlob:
    def __init__(self, backend, path):
        self._backend = backend
        self.name = path

    def upload_from_string(self, content, content_type=None):
        data = content.encode("utf-8") if isinstance(content, str) else content
        self._backend.record(self.name, data)

    def upload_from_file(self, file_obj, content_type=None):
        self._backend.record(self.name, file_obj.read())


class _FakeBucket:
    def __init__(self, backend):
        self._backend = backend

    def blob(self, path):
        return _FakeBlob(self._backend, path)


class FakeStorageBackend:
    """
    In-memory stand-in for a GCS bucket.

    - objects: {blob_path: bytes} of everything successfully uploaded.
    - upload_order: blob paths in the order they were successfully uploaded.
    - failing_paths: suffixes that should raise instead of uploading, to
      simulate a mid-publication failure.
    """

    def __init__(self):
        self.objects = {}
        self.upload_order = []
        self.failing_paths = set()

    def record(self, path, content):
        for pattern in self.failing_paths:
            if path.endswith(pattern):
                raise RuntimeError(
                    f"Simulated GCS upload failure for {path}"
                )

        self.objects[path] = content
        self.upload_order.append(path)


class FakeStorageClient:
    def __init__(self, backend, project=None):
        self._backend = backend
        self.project = project

    def bucket(self, name):
        return _FakeBucket(self._backend)

    def list_blobs(self, bucket, prefix=""):
        return [
            _ListedBlob(name)
            for name in self._backend.objects
            if name.startswith(prefix)
        ]


@pytest.fixture
def fake_storage(monkeypatch):
    """
    Replaces google.cloud.storage.Client with an in-memory fake so
    versioning.py, storage.py and results.py can run unmodified against it.
    Never touches the real GCS bucket.
    """

    backend = FakeStorageBackend()

    monkeypatch.setattr(
        storage_module.storage,
        "Client",
        lambda project=None: FakeStorageClient(backend, project=project),
    )

    return backend


@pytest.fixture
def sample_gold_df():
    """
    Small, deterministic stand-in for the Gold table: 2 municipalities x
    5 months (3 before TEST_START, 2 on/after it), single disease.
    Climate values are offset per municipality so lag-leak tests have
    non-overlapping value ranges to assert against.
    """

    municipalities = ["MUNI_A", "MUNI_B"]
    months = [
        "2023-10-01",
        "2023-11-01",
        "2023-12-01",
        "2024-01-01",
        "2024-02-01",
    ]

    rows = []
    for m_idx, municipality in enumerate(municipalities):
        for month_idx, reference_date in enumerate(months):
            rows.append(
                {
                    "disease": "LEPTOSPIROSE",
                    "municipality": municipality,
                    "reference_date": reference_date,
                    "cases": 5 + m_idx + month_idx,
                    "precipitation_sum_mm": 10.0 * (month_idx + 1) + 100.0 * m_idx,
                    "precipitation_avg_observation_mm": 1.0 * (month_idx + 1),
                    "precipitation_max_observation_mm": 2.0 * (month_idx + 1),
                    "temperature_avg_c": 20.0 + month_idx,
                    "dew_point_avg_c": 15.0 + month_idx,
                    "relative_humidity_avg_pct": 60.0 + month_idx + 10.0 * m_idx,
                    "atmospheric_pressure_avg_mb": 1010.0,
                    "wind_speed_avg_ms": 3.0,
                    "wind_gust_max_ms": 8.0,
                }
            )

    return pd.DataFrame(rows)
