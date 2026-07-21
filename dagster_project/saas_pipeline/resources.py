import os

from dagster_gcp import BigQueryResource
from dotenv import load_dotenv

load_dotenv()

# dagster-gcp's gcp_credentials field writes creds to a NamedTemporaryFile and
# re-opens it for reading, which deadlocks on Windows (exclusive file locks).
# Setting GOOGLE_APPLICATION_CREDENTIALS directly sidesteps that entirely and
# is the standard way google-cloud client libraries expect credentials anyway.
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", os.environ["GCP_SERVICE_ACCOUNT_KEY_PATH"])

bigquery_resource = BigQueryResource(
    project=os.environ["GCP_PROJECT_ID"],
    location=os.environ.get("BQ_LOCATION", "US"),
)
