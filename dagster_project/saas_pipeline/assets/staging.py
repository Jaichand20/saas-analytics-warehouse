"""Staging: clean the raw layer via CREATE OR REPLACE TABLE ... AS SELECT
(sandbox-safe DDL, not DML). Each asset runs one .sql file from
sql/staging/. Orphan-FK rows are quarantined into rejected_* tables rather
than silently dropped.
"""

from pathlib import Path

from dagster import MaterializeResult, MetadataValue, asset
from dagster_gcp import BigQueryResource

from saas_pipeline.sql_utils import run_sql_file

SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "staging"
STAGING_DATASET = "staging"


def _make_staging_asset(table_name, deps):
    @asset(name=table_name, deps=deps)
    def _staging_asset(bigquery: BigQueryResource) -> MaterializeResult:
        sql_path = SQL_DIR / f"{table_name}.sql"
        with bigquery.get_client() as client:
            num_rows = run_sql_file(client, sql_path, STAGING_DATASET, table_name)
        return MaterializeResult(metadata={"num_rows": MetadataValue.int(num_rows)})

    return _staging_asset


stg_accounts = _make_staging_asset("stg_accounts", ["accounts_raw"])
stg_plans = _make_staging_asset("stg_plans", ["plans_raw"])
stg_subscription_events = _make_staging_asset(
    "stg_subscription_events", ["subscription_events_raw", "stg_accounts"]
)
rejected_subscription_events = _make_staging_asset(
    "rejected_subscription_events", ["subscription_events_raw", "stg_accounts"]
)
stg_usage_events = _make_staging_asset("stg_usage_events", ["usage_events_raw"])
stg_invoices = _make_staging_asset("stg_invoices", ["invoices_raw", "stg_accounts"])
rejected_invoices = _make_staging_asset("rejected_invoices", ["invoices_raw", "stg_accounts"])

staging_assets = [
    stg_accounts,
    stg_plans,
    stg_subscription_events,
    rejected_subscription_events,
    stg_usage_events,
    stg_invoices,
    rejected_invoices,
]
