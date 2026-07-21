-- BUSINESS QUESTION: How is monthly recurring revenue trending month over
-- month, and which months grew fastest?
--
-- MRR is a step function: it only changes when a subscription event fires
-- (create/upgrade/downgrade/cancel/reactivate), so a month with no event for
-- an account still has whatever MRR was last set. LAST_VALUE(... IGNORE
-- NULLS) forward-fills across a full account x month grid, then LAG
-- computes the prior month's total for month-over-month growth.

WITH months AS (
  SELECT DISTINCT month_start_date AS month_start
  FROM core.dim_date
  WHERE month_start_date BETWEEN
    (SELECT MIN(DATE_TRUNC(signup_date, MONTH)) FROM core.dim_account)
    AND (SELECT DATE_TRUNC(MAX(event_date), MONTH) FROM core.fct_subscription_events)
),

account_months AS (
  SELECT a.account_id, m.month_start
  FROM core.dim_account a
  CROSS JOIN months m
  WHERE m.month_start >= DATE_TRUNC(a.signup_date, MONTH)
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

account_month_mrr AS (
  SELECT
    am.account_id,
    am.month_start,
    LAST_VALUE(mee.running_mrr IGNORE NULLS) OVER (
      PARTITION BY am.account_id ORDER BY am.month_start
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS account_mrr
  FROM account_months am
  LEFT JOIN month_end_events mee
    ON am.account_id = mee.account_id AND am.month_start = mee.month_start
),

company_month_mrr AS (
  SELECT
    month_start,
    SUM(GREATEST(COALESCE(account_mrr, 0), 0)) AS total_mrr
  FROM account_month_mrr
  GROUP BY month_start
)

SELECT
  month_start,
  total_mrr,
  LAG(total_mrr) OVER (ORDER BY month_start) AS prior_month_mrr,
  total_mrr - LAG(total_mrr) OVER (ORDER BY month_start) AS net_new_mrr,
  ROUND(SAFE_DIVIDE(
    total_mrr - LAG(total_mrr) OVER (ORDER BY month_start),
    LAG(total_mrr) OVER (ORDER BY month_start)
  ) * 100, 1) AS mom_growth_pct
FROM company_month_mrr
ORDER BY month_start
