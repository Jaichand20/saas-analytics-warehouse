# Data Dictionary

Row counts below are a snapshot from the live warehouse, not a guaranteed constant (regenerating the synthetic data or re-running the pipeline will shift them).

## raw

Loaded byte-for-byte from generated CSVs. Every column is `STRING` regardless of logical type — no casting happens until staging — and messiness is intentional and untouched. `_ingested_at` / `source_system` are metadata columns added at load time, used by staging's dedup logic.

| Table | Rows | Columns | Known messiness |
|---|---|---|---|
| `accounts_raw` | 309 | `account_id`, `parent_account_id`, `company_name`, `industry`, `country`, `signup_date`, `employee_count_band`, `_ingested_at`, `source_system` | mixed date formats in `signup_date`; some `parent_account_id` values don't resolve to a real account (orphans) |
| `plans_raw` | 4 | `plan_id`, `plan_name`, `billing_interval`, `list_price_usd`, `tier_rank`, `_ingested_at`, `source_system` | inconsistent `plan_name` casing/format (`"Pro"` / `"PRO"` / `"pro-monthly"`); `list_price_usd` stored as currency-formatted strings (`"$1,200.00"`) |
| `subscription_events_raw` | 744 | `event_id`, `account_id`, `plan_id`, `event_type`, `event_timestamp`, `mrr_delta_usd`, `_ingested_at`, `source_system` | duplicate rows (replayed events); mixed timestamp formats; currency-string `mrr_delta_usd`; some `account_id` orphans |
| `usage_events_raw` | 310,388 | `event_id`, `account_id`, `user_id`, `feature_name`, `event_timestamp`, `usage_units`, `_ingested_at`, `source_system` | duplicate rows; hourly grain (the volume table that motivates daily aggregation downstream) |
| `invoices_raw` | 2,478 | `invoice_id`, `account_id`, `invoice_date`, `amount_due_usd`, `amount_paid_usd`, `status`, `payment_date`, `_ingested_at`, `source_system` | mixed date formats; currency-string amounts; some `account_id` orphans; blank-string vs. NULL inconsistency in `payment_date` |

## staging

Full-refresh `CREATE OR REPLACE TABLE ... AS SELECT`, one cleaning rule per messiness type, each named in `docs/architecture.md`. Row counts drop from `raw` where duplicates are collapsed or rows are quarantined.

| Table | Fix applied |
|---|---|
| `stg_accounts` | Dedup via `QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY _ingested_at DESC) = 1`; date-format coalesce chain on `signup_date`; `parent_account_id` nulled + flagged when orphaned |
| `stg_plans` | Canonical `plan_name` mapped via `LOWER(TRIM(...))` + lookup; currency-string `list_price_usd` cast via `SAFE_CAST(REGEXP_REPLACE(x, r'[$,]', '') AS NUMERIC)` |
| `stg_subscription_events` | Dedup; date-format coalesce; currency-string cast on `mrr_delta_usd`; orphaned `account_id` rows routed to `rejected_subscription_events` |
| `stg_usage_events` | Dedup; currency/number cast on `usage_units` |
| `stg_invoices` | Date-format coalesce; currency-string cast; `NULLIF(TRIM(payment_date), '')` for blank-vs-null; orphaned `account_id` rows routed to `rejected_invoices` |
| `rejected_subscription_events` | Quarantine table — same shape as `stg_subscription_events` plus a `rejection_reason` column |
| `rejected_invoices` | Quarantine table — same shape as `stg_invoices` plus a `rejection_reason` column |

## core

Dimensional model. All types are properly cast (dates as `DATE`, money as `NUMERIC`) — this is the first layer safe to join without defensive casting.

| Table | Rows | Grain | Columns |
|---|---|---|---|
| `dim_account` | 300 | one row per account | `account_id`, `parent_account_id`, `is_parent_orphan` (BOOL), `company_name`, `industry`, `country`, `signup_date`, `employee_count_band` |
| `dim_account_hierarchy` | 300 | one row per account | `account_id`, `root_account_id`, `depth` (INT64), `path` (ARRAY\<STRING\>) — built via `WITH RECURSIVE`, `WHERE depth < 10` cycle guard |
| `dim_plan` | 4 | one row per plan | `plan_id`, `plan_name`, `billing_interval`, `list_price_usd`, `tier_rank` |
| `dim_date` | — | one row per calendar day | `date_day`, `year`, `month`, `month_name`, `quarter`, `day_of_week`, `day_name`, `is_weekend`, `month_start_date`, `year_month` |
| `fct_subscription_events` | 713 | one row per lifecycle event | `event_id`, `account_id`, `plan_id`, `event_type` (create/upgrade/downgrade/cancel/reactivate), `event_timestamp`, `event_date`, `mrr_delta_usd` |
| `fct_invoices` | 2,445 | one row per invoice | `invoice_id`, `account_id`, `invoice_date`, `amount_due_usd`, `amount_paid_usd`, `status`, `payment_date` (nullable — meaningful null for pending) |
| `fct_usage_daily` | 53,404 | one row per (account, feature, day) | `usage_date` (partition key), `account_id`, `feature_name`, `event_count`, `distinct_users`, `total_usage_units` — aggregated from 310,388 hourly `stg_usage_events` rows (~6x reduction), currently covers 2024-01-04 through 2024-09-09 (see `backfill_demo.md` for why it's partial) |

## marts

The only layer Power BI's service account can read. Each table answers one specific business question.

| Table | Rows | Grain | Columns |
|---|---|---|---|
| `mrr_monthly` | 18 | one row per month | `month_start`, `total_mrr`, `active_accounts`, `prior_month_mrr`, `net_new_mrr`, `mom_growth_pct` |
| `churn_risk_accounts` | 212 | one row per active account | `account_id`, `usage_ratio`, `unhealthy_invoices_recent`, `churn_risk_score`, `is_high_risk` (BOOL) — 8 accounts currently flagged high-risk |
| `ltv_by_account` | 300 | one row per account | `account_id`, `company_name`, `industry`, `ltv_usd`, `ltv_quartile`, `ltv_percentile`, `rank_within_industry` |
| `cohort_retention` | 170 | one row per (cohort_month, months_since_signup) | `cohort_month`, `months_since_signup`, `cohort_size`, `active_accounts`, `retention_pct` |
| `enterprise_mrr_rollup` | 207 | one row per root/umbrella account with subsidiaries | `root_account_id`, `root_company_name`, `accounts_in_hierarchy`, `rollup_mrr_usd` |
