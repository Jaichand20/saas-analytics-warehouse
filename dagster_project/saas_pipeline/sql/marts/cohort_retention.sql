-- Retention curve per signup cohort: for every (cohort, months-since-signup)
-- cell - including months where an account had no event at all - is it
-- still active? Reuses the same forward-fill pattern as mrr_monthly.
CREATE OR REPLACE TABLE marts.cohort_retention AS
WITH account_cohort AS (
  SELECT account_id, DATE_TRUNC(signup_date, MONTH) AS cohort_month
  FROM core.dim_account
),
event_running_mrr AS (
  SELECT
    account_id,
    event_date,
    SUM(mrr_delta_usd) OVER (
      PARTITION BY account_id ORDER BY event_timestamp
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_mrr
  FROM core.fct_subscription_events
),
month_end_events AS (
  SELECT account_id, DATE_TRUNC(event_date, MONTH) AS month_start, running_mrr
  FROM event_running_mrr
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, DATE_TRUNC(event_date, MONTH) ORDER BY event_date DESC
  ) = 1
),
months AS (
  SELECT DISTINCT month_start_date AS month_start
  FROM core.dim_date
  WHERE month_start_date BETWEEN
    (SELECT MIN(cohort_month) FROM account_cohort)
    AND (SELECT DATE_TRUNC(MAX(event_date), MONTH) FROM core.fct_subscription_events)
),
account_months AS (
  SELECT ac.account_id, ac.cohort_month, m.month_start
  FROM account_cohort ac
  CROSS JOIN months m
  WHERE m.month_start >= ac.cohort_month
),
account_month_active AS (
  SELECT
    am.account_id,
    am.cohort_month,
    am.month_start,
    LAST_VALUE(mee.running_mrr IGNORE NULLS) OVER (
      PARTITION BY am.account_id ORDER BY am.month_start
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) > 0 AS is_active
  FROM account_months am
  LEFT JOIN month_end_events mee
    ON am.account_id = mee.account_id AND am.month_start = mee.month_start
),
cohort_sizes AS (
  SELECT cohort_month, COUNT(DISTINCT account_id) AS cohort_size
  FROM account_cohort
  GROUP BY cohort_month
)
SELECT
  ama.cohort_month,
  DATE_DIFF(ama.month_start, ama.cohort_month, MONTH) AS months_since_signup,
  cs.cohort_size,
  COUNT(DISTINCT CASE WHEN ama.is_active THEN ama.account_id END) AS active_accounts,
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ama.is_active THEN ama.account_id END),
    cs.cohort_size
  ) AS retention_pct
FROM account_month_active ama
JOIN cohort_sizes cs ON ama.cohort_month = cs.cohort_month
GROUP BY ama.cohort_month, months_since_signup, cs.cohort_size
ORDER BY ama.cohort_month, months_since_signup
