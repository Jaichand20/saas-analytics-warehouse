-- Dedup replayed signup rows, parse mixed-format signup_date, blank out
-- empty-string fields, and null-out + flag any parent_account_id that
-- doesn't point at a real account (rather than dropping the account).
CREATE OR REPLACE TABLE staging.stg_accounts AS
WITH deduped AS (
  SELECT
    account_id,
    NULLIF(TRIM(parent_account_id), '') AS parent_account_id,
    TRIM(company_name) AS company_name,
    NULLIF(TRIM(industry), '') AS industry,
    country,
    COALESCE(
      SAFE.PARSE_DATE('%Y-%m-%d', signup_date),
      SAFE.PARSE_DATE('%m/%d/%Y', signup_date),
      SAFE_CAST(SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', signup_date) AS DATE)
    ) AS signup_date,
    NULLIF(TRIM(employee_count_band), '') AS employee_count_band,
    SAFE_CAST(_ingested_at AS TIMESTAMP) AS _ingested_at
  FROM raw.accounts_raw
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id ORDER BY SAFE_CAST(_ingested_at AS TIMESTAMP) DESC
  ) = 1
)
SELECT
  d.account_id,
  IF(d.parent_account_id IS NOT NULL AND p.account_id IS NULL, NULL, d.parent_account_id) AS parent_account_id,
  (d.parent_account_id IS NOT NULL AND p.account_id IS NULL) AS is_parent_orphan,
  d.company_name,
  d.industry,
  d.country,
  d.signup_date,
  d.employee_count_band,
  d._ingested_at
FROM deduped d
LEFT JOIN deduped p ON d.parent_account_id = p.account_id
