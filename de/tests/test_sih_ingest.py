import pytest

from epidemiological_de import config
from epidemiological_de.sih import ingest


def _entry(size=10):
    return {"size": size, "modified": "02-09-25 09:29PM"}


LISTING = {
    "RDRS1412.dbc": _entry(),  # antes do primeiro ano
    "RDRS1501.dbc": _entry(),
    "RDRS2608.DBC": _entry(),  # o DATASUS mistura maiúsculas na extensão
    "RDSC2401.dbc": _entry(),
    "ERRS2401.dbc": _entry(),  # outro tipo de AIH: fora
    "RDRS2401.dbf": _entry(),
}


def test_tasks_split_all_ufs_without_overlap():
    split = [ingest.task_ufs(i, 27) for i in range(27)]

    assert all(len(ufs) == 1 for ufs in split)
    assert sorted(uf for ufs in split for uf in ufs) == sorted(config.UFS)
    assert ingest.task_ufs(0, 1) == config.UFS


def test_files_to_ingest_filters_uf_type_and_year():
    assert ingest.files_to_ingest(LISTING, ["RS"], 2015) == ["RDRS1501.dbc", "RDRS2608.DBC"]


def test_dbc_path_partitions_by_uf(tmp_path):
    path = ingest.dbc_path("RDRS2401.dbc", root=str(tmp_path))

    assert path.replace("\\", "/").endswith("sih/uf=RS/RDRS2401.dbc")


class FakeClient:
    host = "ftp.test"

    def __init__(self, listing):
        self.listing = listing

    def list_dir(self, directory):
        return self.listing


def test_run_downloads_only_task_ufs_and_reports_failures_at_the_end(tmp_path, monkeypatch):
    calls = []

    def fake_download(client, remote_path, remote, dest, **kwargs):
        calls.append(remote_path)
        if remote_path.endswith("RDRS1501.dbc"):
            raise RuntimeError("FTP caiu")
        return dest

    monkeypatch.setattr(ingest.ingestion, "ftp_download_if_changed", fake_download)
    rs_task = config.UFS.index("RS")

    with pytest.raises(RuntimeError, match="RDRS1501.dbc"):
        ingest.run(FakeClient(LISTING), root=str(tmp_path), task_index=rs_task, task_count=27)

    # A falha em 1501 não impediu 2608 de ser baixado.
    assert [c.split("/")[-1] for c in calls] == ["RDRS1501.dbc", "RDRS2608.DBC"]


def test_run_fails_when_listing_has_nothing_for_the_task(tmp_path):
    with pytest.raises(RuntimeError, match="Nenhum arquivo"):
        ingest.run(FakeClient({}), root=str(tmp_path), task_index=0, task_count=27)
