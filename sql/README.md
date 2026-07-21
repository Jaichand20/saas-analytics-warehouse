# Standalone Showcase Queries

These are self-contained `SELECT` queries meant to be run directly against the warehouse (`core.*` tables) to demonstrate the SQL techniques used throughout this project. They're separate from the pipeline's own materialization SQL (`dagster_project/saas_pipeline/sql/`) - that SQL builds and maintains the warehouse; this SQL is written to be read and run ad hoc by a reviewer.

| Query | Business question | Techniques |
|---|---|---|
| [`01_recursive_enterprise_hierarchy_rollup.sql`](01_recursive_enterprise_hierarchy_rollup.sql) | What's the consolidated MRR of every enterprise umbrella account once you fold in all its subsidiaries (some nested 3 levels deep)? | Recursive CTE (`WITH RECURSIVE`), window function for current-MRR |
| [`02_mrr_growth_lag_window.sql`](02_mrr_growth_lag_window.sql) | How is MRR trending month over month, and which months grew fastest? | `LAST_VALUE(... IGNORE NULLS)` forward-fill, `LAG`, CTE chaining |
| [`03_cohort_retention_curve.sql`](03_cohort_retention_curve.sql) | What fraction of each signup cohort is still active N months later? | Cohort grid via `CROSS JOIN`, forward-fill window function |
| [`04_churn_risk_scoring_cte_subquery.sql`](04_churn_risk_scoring_cte_subquery.sql) | Which active accounts are most at risk of churning? | Chained CTEs blending independent signals, `APPROX_QUANTILES` subquery threshold |
| [`05_ltv_percentile_ranking.sql`](05_ltv_percentile_ranking.sql) | Who are the highest-value customers, overall and within industry? | `NTILE`, `PERCENT_RANK`, `RANK() PARTITION BY` |
| [`06_running_total_revenue.sql`](06_running_total_revenue.sql) | What's cumulative revenue collected to date, and is collection accelerating? | Running total (`SUM() OVER`), rolling average |

Each file opens with a comment block explaining the business question and why that particular technique was the right tool for it - none of these are included just to check a box.
