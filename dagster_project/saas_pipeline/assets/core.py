"""Core: dims and non-partitioned facts built from the staging layer.
dim_account_hierarchy resolves enterprise umbrella/subsidiary account
structures via a recursive CTE; fct_usage_daily (partitioned) lives in
core_partitioned.py.
"""

from pathlib import Path

from dagster import MaterializeResult, MetadataValue, asset
from dagster_gcp import BigQueryResource

from saas_pipeline.sql_utils import run_sql_file

SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "core"
CORE_DATASET = "core"


def _make_core_asset(table_name, deps):
    @asset(name=table_name, deps=deps)
    def _core_asset(bigquery: BigQueryResource) -> MaterializeResult:
        sql_path = SQL_DIR / f"{table_name}.sql"
        with bigquery.get_client() as client:
            num_rows = run_sql_file(client, sql_path, CORE_DATASET, table_name)
        return MaterializeResult(metadata={"num_rows": MetadataValue.int(num_rows)})

    return _core_asset


dim_account = _make_core_asset("dim_account", ["stg_accounts"])
dim_account_hierarchy = _make_core_asset("dim_account_hierarchy", ["dim_account"])
dim_plan = _make_core_asset("dim_plan", ["stg_plans"])
dim_date = _make_core_asset("dim_date", [])
fct_subscription_events = _make_core_asset("fct_subscription_events", ["stg_subscription_events"])
fct_invoices = _make_core_asset("fct_invoices", ["stg_invoices"])

core_assets = [
    dim_account,
    dim_account_hierarchy,
    dim_plan,
    dim_date,
    fct_subscription_events,
    fct_invoices,
]
