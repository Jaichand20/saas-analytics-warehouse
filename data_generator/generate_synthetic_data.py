"""Entrypoint for generating the synthetic SaaS dataset.

Produces intentionally messy raw CSVs (mixed date formats, currency strings,
duplicate rows, orphaned foreign keys) so the Dagster staging layer has real
cleaning work to do, and hourly-grain usage events so the core warehouse layer
has a real hourly-to-daily aggregation story to tell.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from generators.accounts import generate_accounts
from generators.invoices import generate_invoices
from generators.plans import generate_plans
from generators.subscription_events import build_active_intervals, generate_subscription_events
from generators.usage_events import generate_usage_events
from messiness import (
    apply_messy_currency,
    apply_messy_dates,
    blankify,
    duplicate_rows,
    inject_orphan_fk,
    messy_plan_name,
)

SOURCE_SYSTEMS = ["billing_v1", "billing_v2", "crm_export"]
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"


def add_ingestion_metadata(df, rng):
    df = df.copy()
    df["_ingested_at"] = pd.Timestamp("2025-07-01") + pd.to_timedelta(
        rng.integers(0, 60, size=len(df)), unit="D"
    )
    df["source_system"] = rng.choice(SOURCE_SYSTEMS, size=len(df))
    return df


def make_messy_accounts(accounts_df, rng):
    df = add_ingestion_metadata(accounts_df, rng)
    df["signup_date"] = apply_messy_dates(df["signup_date"], rng)
    df["industry"] = blankify(df["industry"], rng, blank_fraction=0.02)
    df["employee_count_band"] = blankify(df["employee_count_band"], rng, blank_fraction=0.02)

    has_parent = df["parent_account_id"].notna()
    df.loc[has_parent, "parent_account_id"] = inject_orphan_fk(
        df.loc[has_parent, "parent_account_id"], rng, orphan_fraction=0.05
    )
    return duplicate_rows(df, rng, dup_fraction=0.03)


def make_messy_plans(plans_df, rng):
    rows = []
    for _, plan in plans_df.iterrows():
        for _ in range(int(rng.integers(1, 3))):
            rows.append(
                {
                    "plan_id": plan["plan_id"],
                    "plan_name": messy_plan_name(plan["plan_name"], rng),
                    "billing_interval": plan["billing_interval"],
                    "list_price_usd": plan["list_price_usd"],
                    "tier_rank": plan["tier_rank"],
                }
            )
    df = pd.DataFrame(rows)
    df = add_ingestion_metadata(df, rng)
    df["list_price_usd"] = apply_messy_currency(df["list_price_usd"], rng)
    return df


def make_messy_subscription_events(events_df, rng):
    df = add_ingestion_metadata(events_df, rng)
    df["event_timestamp"] = apply_messy_dates(df["event_timestamp"], rng)
    df["mrr_delta_usd"] = apply_messy_currency(df["mrr_delta_usd"], rng)
    df["account_id"] = inject_orphan_fk(df["account_id"], rng, orphan_fraction=0.015)
    return duplicate_rows(df, rng, dup_fraction=0.02)


def make_messy_usage_events(usage_df, rng):
    df = add_ingestion_metadata(usage_df, rng)
    df["event_timestamp"] = apply_messy_dates(df["event_timestamp"], rng)
    return duplicate_rows(df, rng, dup_fraction=0.01)


def make_messy_invoices(invoices_df, rng):
    df = add_ingestion_metadata(invoices_df, rng)
    df["invoice_date"] = apply_messy_dates(df["invoice_date"], rng)
    df["payment_date"] = apply_messy_dates(df["payment_date"], rng)
    df["amount_due_usd"] = apply_messy_currency(df["amount_due_usd"], rng)
    df["amount_paid_usd"] = apply_messy_currency(df["amount_paid_usd"], rng)
    df["status"] = df["status"].apply(lambda s: str(rng.choice([s, s.upper(), s.capitalize()])))
    df["account_id"] = inject_orphan_fk(df["account_id"], rng, orphan_fraction=0.015)
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate the synthetic SaaS dataset.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-accounts", type=int, default=300)
    parser.add_argument("--start-date", type=str, default="2024-01-01")
    parser.add_argument("--end-date", type=str, default="2025-06-30")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    faker = Faker()
    Faker.seed(args.seed)

    start_date = pd.Timestamp(args.start_date)
    end_date = pd.Timestamp(args.end_date)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plans_df = generate_plans()
    accounts_df = generate_accounts(rng, faker, args.num_accounts, start_date, end_date)
    subscription_events_df = generate_subscription_events(rng, accounts_df, plans_df, end_date)
    active_intervals = build_active_intervals(subscription_events_df)
    usage_events_df = generate_usage_events(rng, active_intervals, end_date)
    invoices_df = generate_invoices(rng, subscription_events_df, active_intervals, plans_df, end_date)

    outputs = {
        "accounts_raw.csv": make_messy_accounts(accounts_df, rng),
        "plans_raw.csv": make_messy_plans(plans_df, rng),
        "subscription_events_raw.csv": make_messy_subscription_events(subscription_events_df, rng),
        "usage_events_raw.csv": make_messy_usage_events(usage_events_df, rng),
        "invoices_raw.csv": make_messy_invoices(invoices_df, rng),
    }

    for filename, df in outputs.items():
        path = output_dir / filename
        df.to_csv(path, index=False)
        print(f"wrote {len(df):>8,} rows -> {path}")


if __name__ == "__main__":
    main()
