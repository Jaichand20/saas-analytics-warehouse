from dagster import Definitions

from saas_pipeline.resources import bigquery_resource

# Assets are added phase by phase (raw -> staging -> core -> marts).
defs = Definitions(
    assets=[],
    resources={"bigquery": bigquery_resource},
)
