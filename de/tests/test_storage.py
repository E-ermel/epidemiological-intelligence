from epidemiological_de import storage


def test_clear_path_removes_existing_directory_contents(tmp_path):
    target = tmp_path / "silver"
    target.mkdir()
    (target / "part-0.parquet").write_bytes(b"old data")

    storage.clear_path(str(target))

    assert not target.exists()


def test_clear_path_is_idempotent_when_path_does_not_exist(tmp_path):
    target = tmp_path / "does-not-exist"

    storage.clear_path(str(target))
