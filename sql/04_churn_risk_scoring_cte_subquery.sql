-- BUSINESS QUESTION: Which currently-active accounts are most at risk of
-- churning, so a retention team can reach out before they cancel?
--
-- Chains CTEs to blend two independent signals - usage decline (trailing 30
-- days vs. the 30 days before that) and billing health (recent failed/
-- pending invoices) - into one score, then uses an APPROX_QUANTILES
-- subquery to threshold "high risk" at the top quartile.
--
-- Note: the threshold is computed over accounts with a NONZERO score only.
-- Most accounts show no risk signal at all (score = 0), so a percentile
-- over the whole population would sit at 0 and flag everyone - a real bug
-- caught while building marts.churn_risk_accounts (see git history).

WITH usage_bounds AS (
  SELECT MAX(usage_date) AS as_of_date FROM core.fct_usage_daily
),

usage_recent AS (
  SELECT account_id, SUM(total_usage_units) AS usage_units_recent
  FROM core.fct_usage_daily, usage_bounds
  WHERE usage_date BETWEEN DATE_SUB(as_of_date, INTERVAL 30 DAY) AND as_of_date
  GROUP BY account_id
),

usage_prior AS (
  SELECT account_id, SUM(total_usage_units) AS usage_units_prior
  FROM core.fct_usage_daily, usage_bounds
  WHERE usage_date BETWEEN DATE_SUB(as_of_date, INTERVAL 60 DAY) AND DATE_SUB(as_of_date, INTERVAL 31 DAY)
  GROUP BY account_id
),

billing_health AS (
  SELECT account_id, COUNTIF(status IN ('failed', 'pending')) AS unhealthy_invoices_recent
  FROM core.fct_invoices, usage_bounds
  WHERE invoice_date BETWEEN DATE_SUB(as_of_date, INTERVAL 90 DAY) AND as_of_date
  GROUP BY account_id
),

current_status AS (
  SELECT account_id, event_type AS last_event_type
  FROM core.fct_subscription_events
  QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY event_timestamp DESC) = 1
),

risk_inputs AS (
  SELECT
    cs.account_id,
    SAFE_DIVIDE(COALESCE(ur.usage_units_recent, 0), NULLIF(up.usage_units_prior, 0)) AS usage_ratio,
    COALESCE(bh.unhealthy_invoices_recent, 0) AS unhealthy_invoices_recent
  FROM current_status cs
  LEFT JOIN usage_recent ur ON cs.account_id = ur.account_id
  LEFT JOIN usage_prior up ON cs.account_id = up.account_id
  LEFT JOIN billing_health bh ON cs.account_id = bh.account_id
  WHERE cs.last_event_type != 'cancel'
),

scored AS (
  SELECT
    *,
    (1 - LEAST(COALESCE(usage_ratio, 1), 1)) * 0.7
      + LEAST(unhealthy_invoices_recent, 3) / 3.0 * 0.3 AS churn_risk_score
  FROM risk_inputs
),

threshold AS (
  SELECT APPROX_QUANTILES(churn_risk_score, 100)[OFFSET(75)] AS p75_score
  FROM scored
  WHERE churn_risk_score > 0
)

SELECT
  s.account_id,
  ROUND(s.usage_ratio, 2) AS usage_ratio,
  s.unhealthy_invoices_recent,
  ROUND(s.churn_risk_score, 3) AS churn_risk_score
FROM scored s, threshold t
WHERE s.churn_risk_score > 0 AND s.churn_risk_score >= t.p75_score
ORDER BY s.churn_risk_score DESC
