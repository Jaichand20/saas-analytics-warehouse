"""Daily-partitioned usage rollup. Each Dagster partition rebuilds
fct_usage_daily via CREATE OR REPLACE TABLE, preserving every other date's
data and recomputing only its own day. Pure DDL, never DML - gives clean,
idempotent per-partition overwrite/backfill semantics.
"""

from pathlib import Path

from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset
from dagster_gcp import BigQueryResource

from saas_pipeline.partitions import daily_partitions
from saas_pipeline.sql_utils import ensure_dataset

SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "core"
CORE_DATASET = "core"
TABLE_NAME = "fct_usage_daily"


def materialize_usage_partition(client, partition_date):
    """Recomputes one day of fct_usage_daily, leaving every other partition
    untouched. Reused directly (outside Dagster) to backfill full history
    quickly - see docs/backfill_demo.md.
    """
    ensure_dataset(client, CORE_DATASET)

    schema_sql = (SQL_DIR / f"{TABLE_NAME}_schema.sql").read_text(encoding="utf-8")
    client.query(schema_sql).result()

    query_template = (SQL_DIR / f"{TABLE_NAME}.sql").read_text(encoding="utf-8")
    sql = query_template.format(partition_date=partition_date)
    client.query(sql).result()

    count_sql = (
        f"SELECT COUNT(*) AS n FROM `{client.project}.{CORE_DATASET}.{TABLE_NAME}` "
        f"WHERE usage_date = DATE('{partition_date}')"
    )
    return list(client.query(count_sql).result())[0].n


@asset(name=TABLE_NAME, partitions_def=daily_partitions, deps=["stg_usage_events"])
def fct_usage_daily(context: AssetExecutionContext, bigquery: BigQueryResource) -> MaterializeResult:
    partition_date = context.partition_key
    with bigquery.get_client() as client:
        num_rows = materialize_usage_partition(client, partition_date)
    return MaterializeResult(metadata={"num_rows": MetadataValue.int(num_rows)})


core_partitioned_assets = [fct_usage_daily]
