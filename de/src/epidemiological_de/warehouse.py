import pandas as pd
from google.cloud import bigquery

def load_dataframe(df: pd.DataFrame, table_id: str, client: bigquery.Client | None = None) -> int:

    # WRITE_TRUNCATE substitui a tabela inteira, como o
    # write_disposition da antiga task load_gold_bigquery do Airflow.
    client = client or bigquery.Client()

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    # Mesma checagem de contagem que o pipeline já faz depois do to_parquet.
    stored_rows = client.get_table(table_id).num_rows
    if stored_rows != len(df):
        raise ValueError(
            f"BigQuery row count mismatch: "
            f"original={len(df)}, stored={stored_rows}"
        )

    return stored_rows