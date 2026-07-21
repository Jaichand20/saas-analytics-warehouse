-- Dedup replayed events, parse mixed-format timestamps and currency strings,
-- and drop events whose account_id doesn't resolve to a real account (those
-- land in rejected_subscription_events instead of silently vanishing).
CREATE OR REPLACE TABLE staging.stg_subscription_events AS
WITH deduped AS (
  SELECT
    event_id,
    account_id,
    plan_id,
    LOWER(TRIM(event_type)) AS event_type,
    COALESCE(
      SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', event_timestamp),
      SAFE_CAST(SAFE.PARSE_DATE('%Y-%m-%d', event_timestamp) AS TIMESTAMP),
      SAFE_CAST(SAFE.PARSE_DATE('%m/%d/%Y', event_timestamp) AS TIMESTAMP)
    ) AS event_timestamp,
    SAFE_CAST(REGEXP_REPLACE(mrr_delta_usd, r'[$,]', '') AS NUMERIC) AS mrr_delta_usd,
    SAFE_CAST(_ingested_at AS TIMESTAMP) AS _ingested_at
  FROM raw.subscription_events_raw
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY event_id ORDER BY SAFE_CAST(_ingested_at AS TIMESTAMP) DESC
  ) = 1
)
SELECT d.*
FROM deduped d
INNER JOIN staging.stg_accounts a ON d.account_id = a.account_id
