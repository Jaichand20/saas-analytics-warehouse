-- Lifetime value per account, ranked/percentiled against peers and within
-- industry - the basis for the "who's worth protecting" side of the churn
-- story.
CREATE OR REPLACE TABLE marts.ltv_by_account AS
WITH account_ltv AS (
  SELECT
    a.account_id,
    a.company_name,
    a.industry,
    COALESCE(SUM(i.amount_paid_usd), 0) AS ltv_usd
  FROM core.dim_account a
  LEFT JOIN core.fct_invoices i ON a.account_id = i.account_id
  GROUP BY a.account_id, a.company_name, a.industry
)
SELECT
  account_id,
  company_name,
  industry,
  ltv_usd,
  NTILE(4) OVER (ORDER BY ltv_usd) AS ltv_quartile,
  PERCENT_RANK() OVER (ORDER BY ltv_usd) AS ltv_percentile,
  RANK() OVER (PARTITION BY industry ORDER BY ltv_usd DESC) AS rank_within_industry
FROM account_ltv
ORDER BY ltv_usd DESC
