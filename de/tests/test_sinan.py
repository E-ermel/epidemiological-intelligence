import json

import pandas as pd
import pytest

from epidemiological_de import config
from epidemiological_de.sinan import ingest, pipeline, transform


def _entry(size=10):
    return {"size": size, "modified": "07-15-26 02:08PM"}


LISTINGS = {
    "FINAIS": {
        "LEPTBR14.dbc": _entry(),  # antes do primeiro ano
        "LEPTBR24.dbc": _entry(1),
        "ANIMBR22.dbc": _entry(),
        "DENGBR24.dbc": _entry(),  # outro agravo
    },
    "PRELIM": {
        "LEPTBR24.dbc": _entry(2),  # também em FINAIS: vale FINAIS
        "LEPTBR25.dbc": _entry(),
        "animbr26.DBC": _entry(),
    },
}


def test_select_files_prefers_finais_and_filters_agravo_and_year():
    files = ingest.select_files(LISTINGS, ["LEPT", "ANIM"], 2015)

    assert list(files) == ["ANIMBR22.DBC", "ANIMBR26.DBC", "LEPTBR24.DBC", "LEPTBR25.DBC"]
    assert files["LEPTBR24.DBC"] == ("FINAIS", "LEPTBR24.dbc", _entry(1))
    assert files["ANIMBR26.DBC"][:2] == ("PRELIM", "animbr26.DBC")


def test_dbc_path_partitions_by_agravo(tmp_path):
    path = ingest.dbc_path("animbr26.DBC", root=str(tmp_path))

    assert path.replace("\\", "/").endswith("sinan/agravo=ANIM/ANIMBR26.DBC")


class FakeClient:
    host = "ftp.test"

    def __init__(self, listings):
        self.listings = {config.SINAN_FTP_DIRS[folder]: listing for folder, listing in listings.items()}

    def list_dir(self, directory):
        return self.listings[directory]


def test_run_downloads_from_the_chosen_folder(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        ingest.ingestion,
        "ftp_download_if_changed",
        lambda client, remote_path, remote, dest, **kwargs: calls.append(remote_path) or dest,
    )

    ingest.run(FakeClient(LISTINGS), root=str(tmp_path))

    assert f"{config.SINAN_FTP_DIRS['FINAIS']}/LEPTBR24.dbc" in calls
    assert f"{config.SINAN_FTP_DIRS['PRELIM']}/animbr26.DBC" in calls
    assert len(calls) == 4


def test_run_fails_when_an_agravo_is_missing(tmp_path):
    only_lept = {"FINAIS": {"LEPTBR24.dbc": _entry()}, "PRELIM": {}}

    with pytest.raises(RuntimeError, match="ANIM"):
        ingest.run(FakeClient(only_lept), root=str(tmp_path))


def _lept(*rows):
    return pd.DataFrame(rows, columns=transform.LEPT_COLUMNS)


def _anim(*rows):
    return pd.DataFrame(rows, columns=transform.ANIM_COLUMNS)


def test_leptospirosis_counts_confirmed_by_residence_and_infection_place():
    events = transform.leptospirosis_events(
        _lept(
            ("431490", "430460", "20240115", "1"),
            ("431490", "", "20240120", "1"),  # sem local de infecção apurado
            ("431490", "430460", "20240115", "2"),  # descartado: fora
            ("431490", "430460", "20240115", ""),  # sem classificação: fora
        )
    )

    silver = transform.aggregate_cases(events, first_year=2015)

    assert len(silver) == 2
    assert silver["cases"].tolist() == [1, 1]
    assert silver["residence_municipality_code"].tolist() == ["431490", "431490"]
    assert silver["occurrence_municipality_code"].isna().sum() == 1
    assert "430460" in set(silver["occurrence_municipality_code"].dropna())


def test_venomous_accidents_split_by_animal_and_use_accident_place_and_date():
    events = transform.venomous_accident_events(
        _anim(
            ("355030", "350950", "20240301", "20240302", "3"),
            ("355030", "350950", "", "20240405", "1"),  # sem data do acidente: usa sintomas
            ("355030", "355030", "20240301", "20240301", "9"),  # ignorado
            ("355030", "355030", "20240301", "20240301", ""),
        )
    )

    silver = transform.aggregate_cases(events, first_year=2015)
    by_disease = silver.groupby("disease")["cases"].sum().to_dict()

    assert by_disease == {
        "ACIDENTE POR ESCORPIÃO": 1,
        "ACIDENTE POR SERPENTE": 1,
        "ACIDENTE POR OUTRO ANIMAL PEÇONHENTO": 2,
    }
    scorpion = silver[silver["disease"] == "ACIDENTE POR ESCORPIÃO"].iloc[0]
    assert scorpion["occurrence_municipality_code"] == "350950"
    assert silver[silver["disease"] == "ACIDENTE POR SERPENTE"].iloc[0]["month"] == 4


def test_aggregate_drops_events_before_first_year_and_invalid_dates():
    events = transform.leptospirosis_events(
        _lept(("431490", "", "20141230", "1"), ("431490", "", "", "1"), ("431490", "", "20150102", "1"))
    )

    silver = transform.aggregate_cases(events, first_year=2015)

    assert silver[["year", "month", "cases"]].values.tolist() == [[2015, 1, 1]]


def test_combine_sums_december_case_notified_next_year():
    december_in_2024_file = transform.aggregate_cases(
        transform.leptospirosis_events(_lept(("431490", "", "20241228", "1"))), 2015
    )
    december_in_2025_file = transform.aggregate_cases(
        transform.leptospirosis_events(_lept(("431490", "", "20241230", "1"))), 2015
    )

    combined = transform.combine([december_in_2024_file, december_in_2025_file])

    assert combined["cases"].tolist() == [2]


def test_pipeline_writes_silver_for_all_agravos(tmp_path, monkeypatch):
    for agravo, name, folder_name in (("LEPT", "LEPTBR24.DBC", "FINAIS"), ("ANIM", "ANIMBR24.DBC", "PRELIM")):
        folder = tmp_path / "bronze" / "sinan" / f"agravo={agravo}"
        folder.mkdir(parents=True)
        (folder / name).write_bytes(b"")
        (folder / f"{name}.manifest.json").write_text(
            json.dumps({"url": f"ftp://ftp.test/dissemin/publicos/SINAN/DADOS/{folder_name}/{name}"})
        )

    fake_records = {
        tuple(transform.LEPT_COLUMNS): _lept(("431490", "", "20240115", "1")),
        tuple(transform.ANIM_COLUMNS): _anim(("431490", "431490", "20240301", "", "3")),
    }
    monkeypatch.setattr(pipeline.dbc, "read_dbc", lambda path, columns: fake_records[tuple(columns)])

    silver_root = str(tmp_path / "silver")
    pipeline.run(root=str(tmp_path / "bronze"), silver_root=silver_root)

    stored = pd.read_parquet(f"{silver_root}/part-0.parquet").set_index("disease")
    assert sorted(stored.index) == ["ACIDENTE POR ESCORPIÃO", "LEPTOSPIROSE"]
    # ANIM 2024 veio de PRELIM; LEPT 2024 de FINAIS.
    assert bool(stored.loc["ACIDENTE POR ESCORPIÃO", "is_provisional"]) is True
    assert bool(stored.loc["LEPTOSPIROSE", "is_provisional"]) is False
