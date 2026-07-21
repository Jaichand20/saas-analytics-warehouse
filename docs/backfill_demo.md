# Backfill Demo

`core.fct_usage_daily` is a Dagster asset partitioned by day (`DailyPartitionsDefinition`, `dagster_project/saas_pipeline/partitions.py`). Each partition is one calendar day; materializing a partition rebuilds that day's rows in the BigQuery table while every other day's data is left untouched (see `assets/core_partitioned.py` for why: BigQuery blocks true single-partition writes at the API level for us, so each run does a `CREATE OR REPLACE TABLE ... AS SELECT * FROM self WHERE date != target UNION ALL <fresh day>` - pure DDL, still idempotent per day).

## Running a single partition

```bash
cd dagster_project
export PYTHONPATH="$(pwd)"
dagster asset materialize --select fct_usage_daily --partition "2024-03-15" -m saas_pipeline.definitions
```

## Running a backfill over a range (Dagster UI)

The CLI's `--partition-range` flag requires a `BackfillPolicy.single_run()` on the asset, which we deliberately don't use here - per-partition runs make each day's materialization independently idempotent and give a much better visual demo (the partition status grid fills in one day at a time) than a single opaque run covering months of data. To backfill a range:

```bash
cd dagster_project
export PYTHONPATH="$(pwd)"
dagster dev -m saas_pipeline.definitions
```

Then in the browser (`localhost:3000`): Assets -> `fct_usage_daily` -> Materialize -> pick a date range in the backfill launcher. Dagster queues one run per day and the partition grid goes from empty to green as each completes - a good screenshot for a portfolio writeup.

## A real constraint hit while backfilling history

Populating `fct_usage_daily`'s full ~18 months of history (543 distinct days) ran into a genuine BigQuery limit: **"Quota exceeded: Number of partition modifications to a column partitioned table."** This wasn't a bug in the pipeline - it's a hard platform limit on how many times a single date-partitioned table's partitions can be rewritten in a given window, and it applied well below the ~5,000/day figure BigQuery's own docs cite as the default (it isn't exposed through `gcloud alpha services quota list`, so it looks like an internal/managed limit rather than something requestable through the standard quota API - possibly a conservative starter allowance for a project that had only just linked billing).

In practice: a backfill loop hit the wall twice, first after ~249 rapid-fire partition rewrites, then again after just one more following a ~40-minute gap - confirming it isn't a simple "resets at midnight" daily quota but something closer to a short rolling window that recovers slowly. As of this writing, `fct_usage_daily` covers **2024-01-04 through 2024-09-09 (250 days)** out of the full 2024-01-04 to 2025-06-29 range the source data spans. That's enough real daily-grain history for every downstream mart and the dashboard to work correctly; the remaining ~293 days can be filled in gradually (a handful of partitions at a time, spaced out) using the same resumable approach:

```python
# see materialize_usage_partition() in assets/core_partitioned.py -
# call it directly per date, skipping dates already present in the table,
# and stop cleanly on a 403 Forbidden rather than hammering the quota.
```

**The lesson for the README:** real pipelines hit real platform limits, and a good backfill design (idempotent per-partition rebuild, resumable, skip-what's-done) survives that gracefully instead of needing a from-scratch rerun.
