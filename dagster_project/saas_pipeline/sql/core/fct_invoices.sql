CREATE OR REPLACE TABLE core.fct_invoices AS
SELECT
  invoice_id,
  account_id,
  invoice_date,
  amount_due_usd,
  amount_paid_usd,
  status,
  payment_date
FROM staging.stg_invoices
