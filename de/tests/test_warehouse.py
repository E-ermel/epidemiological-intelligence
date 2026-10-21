from types import SimpleNamespace

import pandas as pd
import pytest
from google.cloud import bigquery

from epidemiological_de import warehouse


class FakeClient:
    def __init__(self, stored_rows):
        self.stored_rows = stored_rows
        self.loads = []

    def load_table_from_dataframe(self, df, table_id, job_config):
        self.loads.append((df, table_id, job_config))
        return SimpleNamespace(result=lambda: None)

    def get_table(self, table_id):
        return SimpleNamespace(num_rows=self.stored_rows)


def test_load_dataframe_truncates_table():
    df = pd.DataFrame({"cases": [1, 2, 3]})
    client = FakeClient(stored_rows=3)

    rows = warehouse.load_dataframe(df, "p.d.t", client=client)

    assert rows == 3
    _, table_id, job_config = client.loads[0]
    assert table_id == "p.d.t"
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE


def test_load_dataframe_raises_on_row_count_mismatch():
    df = pd.DataFrame({"cases": [1, 2, 3]})

    with pytest.raises(ValueError, match="row count mismatch"):
        warehouse.load_dataframe(df, "p.d.t", client=FakeClient(stored_rows=2))
