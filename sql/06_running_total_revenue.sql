-- BUSINESS QUESTION: What's our cumulative revenue collected to date, and
-- is month-to-month collection accelerating or flattening?
--
-- Distinct from MRR (a point-in-time recurring-revenue metric): this
-- tracks actual cash collected (paid invoices only), a classic running-
-- total window function, plus a rolling 3-month average to smooth
-- month-to-month noise.

WITH monthly_totals AS (
  SELECT
    DATE_TRUNC(invoice_date, MONTH) AS invoice_month,
    SUM(amount_paid_usd) AS monthly_revenue
  FROM core.fct_invoices
  WHERE status = 'paid'
  GROUP BY invoice_month
)

SELECT
  invoice_month,
  monthly_revenue,
  SUM(monthly_revenue) OVER (
    ORDER BY invoice_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_revenue,
  ROUND(AVG(monthly_revenue) OVER (
    ORDER BY invoice_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  ), 2) AS rolling_3mo_avg_revenue
FROM monthly_totals
ORDER BY invoice_month
