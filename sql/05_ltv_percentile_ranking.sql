-- BUSINESS QUESTION: Who are our highest-value customers, and how does a
-- given account's lifetime value compare to its peers - both overall and
-- within its own industry?
--
-- Three different ranking window functions, each answering a slightly
-- different question: NTILE buckets accounts into value quartiles,
-- PERCENT_RANK gives an exact percentile, RANK (partitioned by industry)
-- shows standing among direct peers.

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
  ROUND(PERCENT_RANK() OVER (ORDER BY ltv_usd), 3) AS ltv_percentile,
  RANK() OVER (PARTITION BY industry ORDER BY ltv_usd DESC) AS rank_within_industry
FROM account_ltv
ORDER BY ltv_usd DESC
