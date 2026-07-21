import os

from dagster_gcp import BigQueryResource
from dotenv import load_dotenv

load_dotenv()

bigquery_resource = BigQueryResource(
    project=os.environ["GCP_PROJECT_ID"],
    gcp_credentials=os.environ.get("GCP_SERVICE_ACCOUNT_KEY_PATH"),
    location=os.environ.get("BQ_LOCATION", "US"),
)
