-- BUSINESS QUESTION: What is the consolidated MRR of every enterprise
-- umbrella account, once you fold in all of its subsidiaries - some of
-- which have their own sub-accounts (depth 3)?
--
-- A plain JOIN can't do this: the depth of the account hierarchy varies per
-- account (some are standalone, some have children, a few have
-- grandchildren), so the number of joins needed isn't known ahead of time.
-- A recursive CTE walks the hierarchy however deep it goes.
--
-- Self-contained: builds the hierarchy from core.dim_account directly
-- (the same logic core.dim_account_hierarchy materializes in the pipeline),
-- then rolls up current MRR to each root account.

WITH RECURSIVE hierarchy AS (
  -- anchor: root accounts (no parent, or a parent that didn't resolve to a
  -- real account - staging already nulled those out and flagged them)
  SELECT
    account_id,
    account_id AS root_account_id,
    0 AS depth
  FROM core.dim_account
  WHERE parent_account_id IS NULL

  UNION ALL

  -- recursive: attach each child to its parent's row, inheriting the
  -- parent's root and incrementing depth. WHERE depth < 10 guards against
  -- accidental cycles.
  SELECT
    child.account_id,
    parent.root_account_id,
    parent.depth + 1
  FROM core.dim_account AS child
  JOIN hierarchy AS parent ON child.parent_account_id = parent.account_id
  WHERE parent.depth < 10
),

current_account_mrr AS (
  -- each account's MRR as of its most recent subscription event - a
  -- running total (SUM ... OVER) that only changes on create/upgrade/
  -- downgrade/cancel/reactivate events, so the last event's running value
  -- is the account's current MRR.
  SELECT
    account_id,
    SUM(mrr_delta_usd) OVER (
      PARTITION BY account_id ORDER BY event_timestamp
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_mrr
  FROM core.fct_subscription_events
  QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY event_timestamp DESC) = 1
)

SELECT
  h.root_account_id,
  root.company_name AS root_company_name,
  COUNT(DISTINCT h.account_id) AS accounts_in_hierarchy,
  MAX(h.depth) AS max_depth,
  SUM(GREATEST(COALESCE(cam.running_mrr, 0), 0)) AS rollup_mrr_usd
FROM hierarchy h
JOIN core.dim_account root ON h.root_account_id = root.account_id
LEFT JOIN current_account_mrr cam ON h.account_id = cam.account_id
GROUP BY h.root_account_id, root.company_name
HAVING COUNT(DISTINCT h.account_id) > 1  -- only show umbrellas that actually have subsidiaries
ORDER BY rollup_mrr_usd DESC
