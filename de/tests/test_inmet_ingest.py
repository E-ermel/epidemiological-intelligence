from datetime import datetime

from epidemiological_de import config
from epidemiological_de.inmet import ingest


def test_years_to_ingest_goes_from_first_year_to_current():
    years = ingest.years_to_ingest(datetime(2026, 10, 22))

    assert years[0] == config.INMET_FIRST_YEAR
    assert years[-1] == 2026


def test_run_downloads_each_year_to_its_partition(tmp_path, monkeypatch):
    calls = []

    def fake_download(url, dest, **kwargs):
        calls.append((url, dest, kwargs["source_type"]))
        return dest

    monkeypatch.setattr(ingest, "years_to_ingest", lambda: [2023, 2024])
    monkeypatch.setattr(ingest.ingestion, "download_if_changed", fake_download)

    written = ingest.run(session=object(), root=str(tmp_path))

    assert set(written) == {2023, 2024}
    url, dest, source_type = calls[1]
    assert url.endswith("/dadoshistoricos/2024.zip")
    assert dest.replace("\\", "/").endswith("inmet/year=2024/2024.zip")
    assert source_type == "oficial"
