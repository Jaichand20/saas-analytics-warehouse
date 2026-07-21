-- Parse mixed-format dates and currency strings, normalize status casing,
-- and drop invoices whose account_id doesn't resolve to a real account
-- (those land in rejected_invoices instead of silently vanishing).
CREATE OR REPLACE TABLE staging.stg_invoices AS
WITH parsed AS (
  SELECT
    invoice_id,
    account_id,
    COALESCE(
      SAFE.PARSE_DATE('%Y-%m-%d', invoice_date),
      SAFE.PARSE_DATE('%m/%d/%Y', invoice_date),
      SAFE_CAST(SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', invoice_date) AS DATE)
    ) AS invoice_date,
    SAFE_CAST(REGEXP_REPLACE(amount_due_usd, r'[$,]', '') AS NUMERIC) AS amount_due_usd,
    SAFE_CAST(REGEXP_REPLACE(amount_paid_usd, r'[$,]', '') AS NUMERIC) AS amount_paid_usd,
    LOWER(TRIM(status)) AS status,
    COALESCE(
      SAFE.PARSE_DATE('%Y-%m-%d', payment_date),
      SAFE.PARSE_DATE('%m/%d/%Y', payment_date),
      SAFE_CAST(SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', payment_date) AS DATE)
    ) AS payment_date,
    SAFE_CAST(_ingested_at AS TIMESTAMP) AS _ingested_at
  FROM raw.invoices_raw
)
SELECT p.*
FROM parsed p
INNER JOIN staging.stg_accounts a ON p.account_id = a.account_id
