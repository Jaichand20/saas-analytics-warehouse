CREATE OR REPLACE TABLE core.dim_account AS
SELECT
  account_id,
  parent_account_id,
  is_parent_orphan,
  company_name,
  industry,
  country,
  signup_date,
  employee_count_band
FROM staging.stg_accounts
