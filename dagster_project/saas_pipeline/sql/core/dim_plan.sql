CREATE OR REPLACE TABLE core.dim_plan AS
SELECT plan_id, plan_name, billing_interval, list_price_usd, tier_rank
FROM staging.stg_plans
