"""Shared helpers for executing this pipeline's materialization SQL against
BigQuery. Every layer (staging/core/marts) follows the same shape: run a
CREATE OR REPLACE TABLE ... AS SELECT statement, report back the row count.
"""

import os

from google.cloud import bigquery

BQ_LOCATION = os.environ.get("BQ_LOCATION", "US")


def ensure_dataset(client, dataset_name):
    dataset_ref = bigquery.DatasetReference(client.project, dataset_name)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = BQ_LOCATION
    client.create_dataset(dataset, exists_ok=True)
    return dataset_ref


def run_sql_file(client, sql_path, dataset_name, table_name):
    """Executes the CREATE OR REPLACE TABLE ... AS SELECT statement in sql_path
    and returns the resulting table's row count.
    """
    ensure_dataset(client, dataset_name)
    sql = sql_path.read_text(encoding="utf-8")
    job = client.query(sql)
    job.result()
    table_ref = bigquery.DatasetReference(client.project, dataset_name).table(table_name)
    return client.get_table(table_ref).num_rows
