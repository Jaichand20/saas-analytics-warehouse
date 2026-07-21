-- Consolidates MRR up to each enterprise umbrella account using
-- dim_account_hierarchy (the recursive-CTE closure table) - this is exactly
-- the rollup a plain JOIN can't do since subsidiary depth varies per account.
CREATE OR REPLACE TABLE marts.enterprise_mrr_rollup AS
WITH current_account_mrr AS (
  SELECT
    account_id,
    SUM(mrr_delta_usd) OVER (
      PARTITION BY account_id ORDER BY event_timestamp
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_mrr
  FROM core.fct_subscription_events
  QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY event_timestamp DESC) = 1
)
SELECT
  h.root_account_id,
  ra.company_name AS root_company_name,
  COUNT(DISTINCT h.account_id) AS accounts_in_hierarchy,
  SUM(GREATEST(COALESCE(cam.running_mrr, 0), 0)) AS rollup_mrr_usd
FROM core.dim_account_hierarchy h
JOIN core.dim_account ra ON h.root_account_id = ra.account_id
LEFT JOIN current_account_mrr cam ON h.account_id = cam.account_id
GROUP BY h.root_account_id, ra.company_name
ORDER BY rollup_mrr_usd DESC
