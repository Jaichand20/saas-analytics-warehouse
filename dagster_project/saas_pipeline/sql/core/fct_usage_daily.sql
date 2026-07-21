-- Rebuilds fct_usage_daily, keeping every other date's partition untouched
-- and recomputing only {partition_date} from the hourly usage_events. Pure
-- DDL (CREATE OR REPLACE TABLE), never DML, so this gives idempotent
-- per-partition overwrite/backfill semantics regardless of BigQuery tier.
CREATE OR REPLACE TABLE core.fct_usage_daily
PARTITION BY usage_date AS
SELECT *
FROM core.fct_usage_daily
WHERE usage_date != DATE('{partition_date}')

UNION ALL

SELECT
  DATE(event_timestamp) AS usage_date,
  account_id,
  feature_name,
  COUNT(*) AS event_count,
  COUNT(DISTINCT user_id) AS distinct_users,
  SUM(usage_units) AS total_usage_units
FROM staging.stg_usage_events
WHERE DATE(event_timestamp) = DATE('{partition_date}')
GROUP BY usage_date, account_id, feature_name
