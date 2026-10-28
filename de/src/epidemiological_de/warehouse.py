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


def load_parquet_uri(uri: str, table_id: str, expected_rows: int, client: bigquery.Client | None = None) -> int:
    """
    Carrega parquets do GCS (`uri` aceita curinga, ex.: gs://b/gold/*.parquet)
    substituindo a tabela. Para tabelas grandes demais para montar num
    DataFrame só, como o gold nacional.
    """

    client = client or bigquery.Client()

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    client.load_table_from_uri(uri, table_id, job_config=job_config).result()

    stored_rows = client.get_table(table_id).num_rows
    if stored_rows != expected_rows:
        raise ValueError(
            f"BigQuery row count mismatch: "
            f"expected={expected_rows}, stored={stored_rows}"
        )

    return stored_rows