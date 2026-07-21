-- Collapse the plan-name variants (same plan re-extracted from different
-- billing source systems with inconsistent casing/formatting) down to one
-- canonical row per plan, keyed on plan_id (always clean) not plan_name.
CREATE OR REPLACE TABLE staging.stg_plans AS
SELECT
  plan_id,
  CASE plan_id
    WHEN 'starter' THEN 'Starter'
    WHEN 'pro' THEN 'Pro'
    WHEN 'business' THEN 'Business'
    WHEN 'enterprise' THEN 'Enterprise'
    ELSE INITCAP(plan_id)
  END AS plan_name,
  billing_interval,
  SAFE_CAST(REGEXP_REPLACE(list_price_usd, r'[$,]', '') AS NUMERIC) AS list_price_usd,
  SAFE_CAST(tier_rank AS INT64) AS tier_rank
FROM raw.plans_raw
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY plan_id ORDER BY SAFE_CAST(_ingested_at AS TIMESTAMP) DESC
) = 1
