"""Raw ingestion: run the synthetic data generator, then load each messy CSV
into the `raw` BigQuery dataset via a load job (not DML/streaming, so this
works under the BigQuery sandbox's restrictions). Every column lands as
STRING - the raw layer keeps the data exactly as "extracted"; parsing and
type-casting is the staging layer's job.
"""

import sys
from pathlib import Path

from dagster import MaterializeResult, MetadataValue, asset
from dagster_gcp import BigQueryResource
from dotenv import load_dotenv
from google.cloud import bigquery

from saas_pipeline.sql_utils import ensure_dataset

load_dotenv()

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[3] / "data_generator"
if str(DATA_GENERATOR_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_GENERATOR_DIR))

from generate_synthetic_data import DEFAULT_OUTPUT_DIR, generate_dataset  # noqa: E402

RAW_DATASET = "raw"

RAW_TABLES = {
    "accounts_raw": "accounts_raw.csv",
    "plans_raw": "plans_raw.csv",
    "subscription_events_raw": "subscription_events_raw.csv",
    "usage_events_raw": "usage_events_raw.csv",
    "invoices_raw": "invoices_raw.csv",
}


@asset
def synthetic_dataset_files() -> MaterializeResult:
    """Generates the messy synthetic SaaS CSVs on disk (deterministic, seeded)."""
    outputs = generate_dataset()
    return MaterializeResult(
        metadata={f"{name}_rows": MetadataValue.int(len(df)) for name, df in outputs.items()}
    )


def _load_csv_as_raw_table(client, csv_path, table_name):
    dataset_ref = ensure_dataset(client, RAW_DATASET)

    with open(csv_path, "rb") as source_file:
        header = source_file.readline().decode("utf-8").strip().split(",")
        source_file.seek(0)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            schema=[bigquery.SchemaField(col, "STRING") for col in header],
        )
        table_ref = dataset_ref.table(table_name)
        load_job = client.load_table_from_file(source_file, table_ref, job_config=job_config)
        load_job.result()

    return client.get_table(table_ref).num_rows


def _make_raw_ingestion_asset(table_name, csv_filename):
    @asset(name=table_name, deps=["synthetic_dataset_files"])
    def _raw_asset(bigquery: BigQueryResource) -> MaterializeResult:
        csv_path = DEFAULT_OUTPUT_DIR / csv_filename
        with bigquery.get_client() as client:
            num_rows = _load_csv_as_raw_table(client, csv_path, table_name)
        return MaterializeResult(metadata={"num_rows": MetadataValue.int(num_rows)})

    return _raw_asset


accounts_raw = _make_raw_ingestion_asset("accounts_raw", "accounts_raw.csv")
plans_raw = _make_raw_ingestion_asset("plans_raw", "plans_raw.csv")
subscription_events_raw = _make_raw_ingestion_asset("subscription_events_raw", "subscription_events_raw.csv")
usage_events_raw = _make_raw_ingestion_asset("usage_events_raw", "usage_events_raw.csv")
invoices_raw = _make_raw_ingestion_asset("invoices_raw", "invoices_raw.csv")

raw_assets = [
    synthetic_dataset_files,
    accounts_raw,
    plans_raw,
    subscription_events_raw,
    usage_events_raw,
    invoices_raw,
]
