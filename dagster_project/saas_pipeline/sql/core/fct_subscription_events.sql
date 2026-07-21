CREATE OR REPLACE TABLE core.fct_subscription_events AS
SELECT
  event_id,
  account_id,
  plan_id,
  event_type,
  event_timestamp,
  DATE(event_timestamp) AS event_date,
  mrr_delta_usd
FROM staging.stg_subscription_events
