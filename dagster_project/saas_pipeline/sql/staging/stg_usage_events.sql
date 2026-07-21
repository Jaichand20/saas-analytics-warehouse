-- Dedup replayed usage events and parse mixed-format timestamps. No orphan
-- check here (usage volume is high and every event was generated against a
-- real account), unlike subscription_events/invoices.
CREATE OR REPLACE TABLE staging.stg_usage_events AS
SELECT
  event_id,
  account_id,
  user_id,
  feature_name,
  COALESCE(
    SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', event_timestamp),
    SAFE_CAST(SAFE.PARSE_DATE('%Y-%m-%d', event_timestamp) AS TIMESTAMP),
    SAFE_CAST(SAFE.PARSE_DATE('%m/%d/%Y', event_timestamp) AS TIMESTAMP)
  ) AS event_timestamp,
  SAFE_CAST(usage_units AS NUMERIC) AS usage_units,
  SAFE_CAST(_ingested_at AS TIMESTAMP) AS _ingested_at
FROM raw.usage_events_raw
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY event_id ORDER BY SAFE_CAST(_ingested_at AS TIMESTAMP) DESC
) = 1
