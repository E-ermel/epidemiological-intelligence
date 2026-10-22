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


# ---------------------------------------------------------------------
# download_if_changed
# ---------------------------------------------------------------------


class FakeStreamResponse:
    def __init__(self, status_code=200, headers=None, body=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, chunk_size):
        for start in range(0, len(self.body), 3):
            yield self.body[start:start + 3]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeFileServer:
    """Serve um arquivo com ETag; `body_override` simula download truncado."""

    def __init__(self, body, etag, body_override=None):
        self.body, self.etag, self.body_override = body, etag, body_override
        self.gets = 0

    def _headers(self):
        return {"ETag": self.etag, "Last-Modified": "x", "Content-Length": str(len(self.body))}

    def head(self, url, timeout, allow_redirects):
        return FakeStreamResponse(headers=self._headers())

    def get(self, url, timeout, stream):
        self.gets += 1
        body = self.body if self.body_override is None else self.body_override
        return FakeStreamResponse(headers=self._headers(), body=body)


def _download(server, dest):
    return ingestion.download_if_changed(
        "https://x/2024.zip", dest, source="inmet", source_type="oficial", session=server
    )


def test_download_if_changed_streams_file_and_writes_manifest(tmp_path):
    dest = str(tmp_path / "inmet" / "year=2024" / "2024.zip")

    assert _download(FakeFileServer(b"zip-bytes", '"v1"'), dest) == dest

    with open(dest, "rb") as f:
        assert f.read() == b"zip-bytes"
    manifest = ingestion.read_manifest(dest)
    assert manifest["remote"]["etag"] == '"v1"'
    assert manifest["size_bytes"] == 9


def test_download_if_changed_skips_when_etag_unchanged(tmp_path):
    dest = str(tmp_path / "2024.zip")
    _download(FakeFileServer(b"zip-bytes", '"v1"'), dest)

    server = FakeFileServer(b"zip-bytes", '"v1"')
    assert _download(server, dest) is None
    assert server.gets == 0


def test_download_if_changed_redownloads_revised_file(tmp_path):
    dest = str(tmp_path / "2024.zip")
    _download(FakeFileServer(b"old", '"v1"'), dest)

    assert _download(FakeFileServer(b"revised", '"v2"'), dest) == dest
    with open(dest, "rb") as f:
        assert f.read() == b"revised"


def test_truncated_download_fails_and_keeps_previous_version(tmp_path):
    dest = str(tmp_path / "2024.zip")
    _download(FakeFileServer(b"good-version", '"v1"'), dest)

    truncated = FakeFileServer(b"new-version-full", '"v2"', body_override=b"new-ver")
    with pytest.raises(RuntimeError, match="incompleto"):
        _download(truncated, dest)

    with open(dest, "rb") as f:
        assert f.read() == b"good-version"
    assert ingestion.read_manifest(dest)["remote"]["etag"] == '"v1"'
