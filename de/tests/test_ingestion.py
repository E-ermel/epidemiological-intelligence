import json
from datetime import date

import pytest
import requests

from epidemiological_de import ingestion


class FakeResponse:
    def __init__(self, status_code: int, content: bytes = b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class FakeSession:
    """Devolve as respostas (ou exceções) na ordem, uma por chamada."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(ingestion.time, "sleep", lambda seconds: None)


# ---------------------------------------------------------------------
# http_get
# ---------------------------------------------------------------------


def test_http_get_retries_transient_errors_then_succeeds():
    session = FakeSession(
        requests.ConnectionError("reset"),
        FakeResponse(503),
        FakeResponse(200, b"ok"),
    )

    assert ingestion.http_get("https://x", session=session) == b"ok"
    assert session.calls == 3


def test_http_get_fails_fast_on_client_error():
    session = FakeSession(FakeResponse(404))

    with pytest.raises(requests.HTTPError):
        ingestion.http_get("https://x", session=session)

    assert session.calls == 1


def test_http_get_gives_up_after_max_retries():
    session = FakeSession(*[FakeResponse(502) for _ in range(3)])

    with pytest.raises(RuntimeError, match="após 3 tentativas"):
        ingestion.http_get("https://x", session=session, retries=3)


# ---------------------------------------------------------------------
# save_snapshot / latest_file
# ---------------------------------------------------------------------


def _save(root, content, day, source_type="oficial"):
    return ingestion.save_snapshot(
        content,
        source="ibge",
        filename="municipios.json",
        url="https://x/municipios",
        source_type=source_type,
        ingestion_date=day,
        root=str(root),
    )


def test_save_snapshot_writes_file_and_manifest(tmp_path):
    path = _save(tmp_path, b"[1, 2]", date(2026, 10, 1))

    assert path.endswith("ibge/ingestion_date=2026-10-01/municipios.json")
    with open(path, "rb") as f:
        assert f.read() == b"[1, 2]"

    manifest = ingestion.read_manifest(path)
    assert manifest["source_type"] == "oficial"
    assert manifest["url"] == "https://x/municipios"
    assert manifest["size_bytes"] == 6
    assert len(manifest["sha256"]) == 64


def test_save_snapshot_skips_unchanged_content(tmp_path):
    _save(tmp_path, b"[1, 2]", date(2026, 10, 1))

    assert _save(tmp_path, b"[1, 2]", date(2026, 11, 1)) is None
    assert not (tmp_path / "ibge" / "ingestion_date=2026-11-01").exists()


def test_latest_file_returns_newest_changed_snapshot(tmp_path):
    _save(tmp_path, b"v1", date(2026, 9, 1))
    _save(tmp_path, b"v2", date(2026, 10, 1))
    _save(tmp_path, b"v2", date(2026, 11, 1))  # sem mudança: não grava

    latest = ingestion.latest_file("ibge", "municipios.json", root=str(tmp_path))

    assert "ingestion_date=2026-10-01" in latest
    with open(latest, "rb") as f:
        assert f.read() == b"v2"


def test_latest_file_none_when_never_ingested(tmp_path):
    assert ingestion.latest_file("ibge", "municipios.json", root=str(tmp_path)) is None


def test_save_snapshot_rejects_unknown_source_type(tmp_path):
    with pytest.raises(ValueError, match="source_type"):
        _save(tmp_path, b"x", date(2026, 10, 1), source_type="blog")
