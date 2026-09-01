import json

import pytest

from epidemiological_agent.tools import model_tools


@pytest.fixture(autouse=True)
def _clean_metadata_cache():
    model_tools._metadata_cache.clear()
    yield
    model_tools._metadata_cache.clear()


class _FakeBlob:
    def __init__(self, content: str):
        self._content = content

    def exists(self) -> bool:
        return True

    def download_as_text(self, encoding: str = "utf-8") -> str:
        return self._content


def test_invalidate_specific_disease_removes_only_that_entry():
    model_tools._metadata_cache["ASMA"] = (0.0, {"disease": "ASMA"})
    model_tools._metadata_cache["LEPTOSPIROSE"] = (0.0, {"disease": "LEPTOSPIROSE"})

    model_tools.invalidate_model_metadata_cache("ASMA")

    assert "ASMA" not in model_tools._metadata_cache
    assert "LEPTOSPIROSE" in model_tools._metadata_cache


def test_invalidate_with_no_disease_clears_everything():
    model_tools._metadata_cache["ASMA"] = (0.0, None)
    model_tools._metadata_cache["LEPTOSPIROSE"] = (0.0, {"disease": "LEPTOSPIROSE"})

    model_tools.invalidate_model_metadata_cache()

    assert model_tools._metadata_cache == {}


def test_get_model_metadata_rereads_gcs_after_invalidate(monkeypatch):
    """
    Regression test for the bug where a successful retrain didn't show
    up in the UI: get_model_metadata() caches its result (including a
    "not found" miss) for 5 minutes, so without invalidation a disease
    queried before its retrain finished would keep reporting "no model"
    long after a fresh metadata.json actually landed in GCS.
    """

    monkeypatch.setattr(
        model_tools,
        "_get_versioned_artifact_path",
        lambda disease, filename: "modeling/asma/v1/metadata.json",
    )

    responses = iter(
        [
            json.dumps({"model_version": "v1"}),
            json.dumps({"model_version": "v2"}),
        ]
    )

    class _FakeBucket:
        def blob(self, path):
            return _FakeBlob(next(responses))

    monkeypatch.setattr(model_tools, "_get_bucket", lambda: _FakeBucket())

    first = model_tools.get_model_metadata("ASMA")
    assert first["model_version"] == "v1"

    # Still within the TTL -- same cached value, second GCS response
    # (v2) hasn't been consumed yet.
    still_cached = model_tools.get_model_metadata("ASMA")
    assert still_cached["model_version"] == "v1"

    model_tools.invalidate_model_metadata_cache("ASMA")

    fresh = model_tools.get_model_metadata("ASMA")
    assert fresh["model_version"] == "v2"
