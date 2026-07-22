# DAX Measures

Add these in Power BI as new measures (Model view -> right-click the relevant table -> New Measure).

## On `mrr_monthly`

```dax
Total MRR = MAX(mrr_monthly[total_mrr])
```
Latest month's total MRR. Use `MAX` (not `SUM`) since `mrr_monthly` is already one row per month - summing across months would double-count.

```dax
Net New MRR (Latest Month) =
VAR LatestMonth = CALCULATE(MAX(mrr_monthly[month_start]))
RETURN
CALCULATE(
    SUM(mrr_monthly[net_new_mrr]),
    mrr_monthly[month_start] = LatestMonth
)
```
(A nested `CALCULATE` isn't allowed directly inside another `CALCULATE`'s boolean filter argument - DAX requires the inner value be resolved first via a `VAR`.)

```dax
MoM Growth % (Latest Month) =
VAR LatestMonth = CALCULATE(MAX(mrr_monthly[month_start]))
RETURN
CALCULATE(
    SUM(mrr_monthly[mom_growth_pct]),
    mrr_monthly[month_start] = LatestMonth
) * 100
```

## On `churn_risk_accounts`

```dax
High Risk Accounts = CALCULATE(COUNTROWS(churn_risk_accounts), churn_risk_accounts[is_high_risk] = TRUE())
```

```dax
Churn Rate % = DIVIDE([High Risk Accounts], COUNTROWS(churn_risk_accounts)) * 100
```

## On `ltv_by_account`

```dax
Average LTV = AVERAGE(ltv_by_account[ltv_usd])
```

## On `cohort_retention`

```dax
Retention % (Month N) =
CALCULATE(
    AVERAGE(cohort_retention[retention_pct]),
    cohort_retention[months_since_signup] = SELECTEDVALUE(cohort_retention[months_since_signup])
)
```
(Used as the value on a line chart with `months_since_signup` on the axis and `cohort_month` as the legend/series - Power BI evaluates this per axis point automatically, so the explicit filter is mostly documentation of intent.)

## Headline card: Estimated Annual Savings

The math, computed directly from the warehouse (not invented): as of the current data, **8 accounts** are flagged `is_high_risk`, representing **$2,023/month** in combined current MRR - **$24,276/year** in annualized recurring revenue that churns if nothing is done.

```dax
At-Risk ARR =
SUMX(
    FILTER(churn_risk_accounts, churn_risk_accounts[is_high_risk] = TRUE()),
    -- join to a current-MRR-per-account measure/table if modeled, or hardcode
    -- the $24,276 figure computed via sql/04_churn_risk_scoring_cte_subquery.sql
    -- joined to current MRR (see that query's sibling calc in the mart build)
    0
) * 12
```

Simplest to implement directly as a Power BI measure without adding a new relationship: since the at-risk ARR was computed once against the warehouse (`$24,276`), and a realistic proactive-retention program doesn't save 100% of at-risk revenue, the card should show the math transparently rather than a single opaque number:

```dax
Estimated Annual Savings ($) = 24276 * 0.4
```

This assumes a **40% intervention success rate** - a conservative, commonly-cited figure for proactive churn outreach (reaching out to at-risk accounts before they cancel). Displayed as **~$9,710/year**. Label the card "Estimated Annual Savings (assumes 40% successful retention rate on flagged accounts)" so the assumption is visible, not hidden - this number is a projection based on the flagged accounts' current MRR, not a guarantee.
