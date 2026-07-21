-- Flags currently-active accounts at risk of churning: usage-decline signal
-- (trailing 30 days vs the 30 before that) blended with billing health
-- (recent failed/pending invoices), thresholded at the 75th percentile of
-- the resulting score via an APPROX_QUANTILES subquery.
CREATE OR REPLACE TABLE marts.churn_risk_accounts AS
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
    COALESCE(ur.usage_units_recent, 0) AS usage_units_recent,
    COALESCE(up.usage_units_prior, 0) AS usage_units_prior,
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
  -- percentile is computed only over accounts showing *any* risk signal -
  -- most accounts score exactly 0 (no usage decline, no billing issues), so
  -- a percentile over the whole population would sit at 0 and flag everyone
  SELECT APPROX_QUANTILES(churn_risk_score, 100)[OFFSET(75)] AS p75_score
  FROM scored
  WHERE churn_risk_score > 0
)
SELECT
  s.account_id,
  s.usage_units_recent,
  s.usage_units_prior,
  s.usage_ratio,
  s.unhealthy_invoices_recent,
  s.churn_risk_score,
  s.churn_risk_score > 0 AND s.churn_risk_score >= t.p75_score AS is_high_risk
FROM scored s, threshold t
ORDER BY s.churn_risk_score DESC
