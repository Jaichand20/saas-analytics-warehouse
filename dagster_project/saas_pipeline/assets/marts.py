"""Marts: business-ready aggregates that answer the project's actual
questions (MRR growth, churn risk, LTV, cohort retention, enterprise
rollup). Each asset runs one .sql file from sql/marts/.
"""

from pathlib import Path

from dagster import MaterializeResult, MetadataValue, asset
from dagster_gcp import BigQueryResource

from saas_pipeline.sql_utils import run_sql_file

SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "marts"
MARTS_DATASET = "marts"


def _make_mart_asset(table_name, deps):
    @asset(name=table_name, deps=deps)
    def _mart_asset(bigquery: BigQueryResource) -> MaterializeResult:
        sql_path = SQL_DIR / f"{table_name}.sql"
        with bigquery.get_client() as client:
            num_rows = run_sql_file(client, sql_path, MARTS_DATASET, table_name)
        return MaterializeResult(metadata={"num_rows": MetadataValue.int(num_rows)})

    return _mart_asset


mrr_monthly = _make_mart_asset("mrr_monthly", ["fct_subscription_events", "dim_account", "dim_date"])
cohort_retention = _make_mart_asset("cohort_retention", ["fct_subscription_events", "dim_account", "dim_date"])
churn_risk_accounts = _make_mart_asset(
    "churn_risk_accounts", ["fct_usage_daily", "fct_invoices", "fct_subscription_events"]
)
ltv_by_account = _make_mart_asset("ltv_by_account", ["dim_account", "fct_invoices"])
enterprise_mrr_rollup = _make_mart_asset(
    "enterprise_mrr_rollup", ["dim_account_hierarchy", "dim_account", "fct_subscription_events"]
)

marts_assets = [
    mrr_monthly,
    cohort_retention,
    churn_risk_accounts,
    ltv_by_account,
    enterprise_mrr_rollup,
]
