from dagster import Definitions

from saas_pipeline.assets.core import core_assets
from saas_pipeline.assets.core_partitioned import core_partitioned_assets
from saas_pipeline.assets.marts import marts_assets
from saas_pipeline.assets.raw import raw_assets
from saas_pipeline.assets.staging import staging_assets
from saas_pipeline.resources import bigquery_resource

# Assets are added phase by phase (raw -> staging -> core -> marts).
defs = Definitions(
    assets=[*raw_assets, *staging_assets, *core_assets, *core_partitioned_assets, *marts_assets],
    resources={"bigquery": bigquery_resource},
)
