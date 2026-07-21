# Power BI Data Model

## Connecting to BigQuery

1. Power BI Desktop -> **Get Data** -> **Database** -> **Google BigQuery**.
2. Sign-in method: **Service Account Login**.
3. Service account email: `powerbi-reader@saas-analytics-wh-26.iam.gserviceaccount.com`
4. Service account JSON key: paste the contents of `secrets/powerbi-reader-key.json` (in Power BI's dialog, this needs to be the key file's JSON flattened to a single line - copy the whole file's content, it works as-is since it has no embedded newlines outside the `private_key` field's `\n` escapes, which stay as literal `\n` characters in the JSON string).
5. Navigator: expand `saas-analytics-wh-26` -> `marts` and select all 5 tables. **Import** mode (not DirectQuery) - the mart tables are small, business-ready aggregates, so importing avoids live query cost/latency on every dashboard interaction.

This service account (`powerbi-reader`) is scoped to least privilege: `roles/bigquery.jobUser` at the project level (needed to run queries) plus `READER` access on just the `marts` dataset (verified: it can query `marts.*` but is denied on `core`/`staging`/`raw`). It cannot see raw or staging data, only the business-ready mart outputs.

## Tables and schema

| Table | Grain | Key columns |
|---|---|---|
| `mrr_monthly` | one row per month | `month_start` (date), `total_mrr`, `active_accounts`, `prior_month_mrr`, `net_new_mrr`, `mom_growth_pct` |
| `cohort_retention` | one row per (cohort_month, months_since_signup) | `cohort_month` (date), `months_since_signup` (int), `cohort_size`, `active_accounts`, `retention_pct` |
| `churn_risk_accounts` | one row per active account | `account_id`, `usage_ratio`, `unhealthy_invoices_recent`, `churn_risk_score`, `is_high_risk` (bool) |
| `ltv_by_account` | one row per account | `account_id`, `company_name`, `industry`, `ltv_usd`, `ltv_quartile`, `ltv_percentile`, `rank_within_industry` |
| `enterprise_mrr_rollup` | one row per root/umbrella account | `root_account_id`, `root_company_name`, `accounts_in_hierarchy`, `rollup_mrr_usd` |

## Relationships to create in Power BI's model view

`churn_risk_accounts.account_id` -> `ltv_by_account.account_id` (one-to-one) is the only relationship needed to join the two account-grain tables together (e.g. for a "risk vs. value" scatter plot). `mrr_monthly`, `cohort_retention`, and `enterprise_mrr_rollup` are each already fully aggregated and don't need relationships to the others for the visuals in this dashboard - Power BI will treat them as independent tables, which is correct since they're at different grains (month, cohort/month, account, root-account).

## Suggested pages

1. **Overview** - Total MRR card, MRR trend line (`mrr_monthly`), headline "Estimated Annual Savings" card (see `measures.md`).
2. **Churn Risk** - table of `churn_risk_accounts` filtered to `is_high_risk`, joined to `ltv_by_account` for value context; a risk-score vs. LTV scatter.
3. **Retention** - cohort retention curve/heatmap from `cohort_retention` (months_since_signup on the x-axis, one line/row per cohort_month).
4. **Enterprise Accounts** - `enterprise_mrr_rollup` bar chart, sorted descending, to show where consolidated enterprise revenue concentrates.
