-- Calendar spine used by the cohort-retention and MRR-growth marts.
CREATE OR REPLACE TABLE core.dim_date AS
SELECT
  date_day,
  EXTRACT(YEAR FROM date_day) AS year,
  EXTRACT(MONTH FROM date_day) AS month,
  FORMAT_DATE('%B', date_day) AS month_name,
  EXTRACT(QUARTER FROM date_day) AS quarter,
  EXTRACT(DAYOFWEEK FROM date_day) AS day_of_week,
  FORMAT_DATE('%A', date_day) AS day_name,
  EXTRACT(DAYOFWEEK FROM date_day) IN (1, 7) AS is_weekend,
  DATE_TRUNC(date_day, MONTH) AS month_start_date,
  FORMAT_DATE('%Y-%m', date_day) AS year_month
FROM UNNEST(GENERATE_DATE_ARRAY('2023-01-01', '2026-12-31')) AS date_day
