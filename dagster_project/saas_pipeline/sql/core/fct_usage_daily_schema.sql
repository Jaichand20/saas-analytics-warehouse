-- Bootstraps the empty partitioned table on first run (idempotent no-op
-- afterward). Needed so the per-partition rebuild query always has a table
-- to read the "other partitions" from, even before any partition exists.
CREATE TABLE IF NOT EXISTS core.fct_usage_daily (
  usage_date DATE,
  account_id STRING,
  feature_name STRING,
  event_count INT64,
  distinct_users INT64,
  total_usage_units NUMERIC
)
PARTITION BY usage_date
