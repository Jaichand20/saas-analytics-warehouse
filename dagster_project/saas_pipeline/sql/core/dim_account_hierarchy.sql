-- Enterprise umbrella accounts have subsidiary sub-accounts, sometimes nested
-- two levels deep. Depth is unknown per account and a plain JOIN can't roll
-- MRR up to the top-level umbrella, so this is a genuine recursive-CTE
-- problem, not a decorative one. WHERE depth < 10 guards against accidental
-- cycles in the generated data.
CREATE OR REPLACE TABLE core.dim_account_hierarchy AS
WITH RECURSIVE hierarchy AS (
  SELECT
    account_id,
    account_id AS root_account_id,
    0 AS depth,
    [account_id] AS path
  FROM core.dim_account
  WHERE parent_account_id IS NULL

  UNION ALL

  SELECT
    child.account_id,
    parent.root_account_id,
    parent.depth + 1,
    ARRAY_CONCAT(parent.path, [child.account_id])
  FROM core.dim_account AS child
  JOIN hierarchy AS parent ON child.parent_account_id = parent.account_id
  WHERE parent.depth < 10
)
SELECT account_id, root_account_id, depth, path
FROM hierarchy
