"""Shared helpers for injecting realistic data-quality issues into the synthetic dataset."""

import pandas as pd

PLAN_NAME_VARIANTS = {
    "Starter": ["Starter", "STARTER", "starter-monthly", "Starter Monthly"],
    "Pro": ["Pro", "PRO", "pro-monthly", "Pro Monthly"],
    "Business": ["Business", "BUSINESS", "business-monthly", "Business Monthly"],
    "Enterprise": ["Enterprise", "ENTERPRISE", "enterprise-annual", "Enterprise Annual"],
}


def messy_date_string(date_value, rng):
    if pd.isna(date_value):
        return date_value
    fmt = rng.choice(["iso_date", "us_date", "iso_datetime"])
    if fmt == "iso_date":
        return date_value.strftime("%Y-%m-%d")
    if fmt == "us_date":
        return date_value.strftime("%m/%d/%Y")
    return date_value.strftime("%Y-%m-%dT%H:%M:%S")


def messy_currency_string(amount, rng):
    if pd.isna(amount):
        return amount
    style = rng.choice(["plain", "dollar_no_comma", "dollar_comma"])
    if style == "plain":
        return f"{amount:.2f}"
    if style == "dollar_no_comma":
        return f"${amount:.2f}"
    return f"${amount:,.2f}"


def apply_messy_dates(series, rng):
    return series.apply(lambda v: messy_date_string(v, rng))


def apply_messy_currency(series, rng):
    return series.apply(lambda v: messy_currency_string(v, rng))


def blankify(series, rng, blank_fraction=0.03):
    mask = rng.random(len(series)) < blank_fraction
    out = series.copy()
    out.loc[mask & out.notna()] = ""
    return out


def duplicate_rows(df, rng, dup_fraction=0.03, ingested_at_col="_ingested_at"):
    """Replay a random subset of rows with a slightly later ingestion timestamp."""
    if len(df) == 0:
        return df
    n_dupes = max(1, int(len(df) * dup_fraction))
    dupe_idx = rng.choice(df.index, size=n_dupes, replace=False)
    dupes = df.loc[dupe_idx].copy()
    if ingested_at_col in dupes.columns:
        dupes[ingested_at_col] = dupes[ingested_at_col] + pd.Timedelta(hours=1)
    return pd.concat([df, dupes], ignore_index=True)


def inject_orphan_fk(series, rng, orphan_fraction=0.02, ghost_prefix="ghost"):
    """Point a small fraction of foreign keys at IDs that don't exist in the parent table."""
    out = series.copy()
    mask = rng.random(len(out)) < orphan_fraction
    n_ghosts = int(mask.sum())
    if n_ghosts:
        ghost_ids = [f"{ghost_prefix}_{i:04d}" for i in range(n_ghosts)]
        out.loc[mask] = ghost_ids
    return out


def messy_plan_name(canonical_name, rng):
    options = PLAN_NAME_VARIANTS.get(canonical_name, [canonical_name])
    return rng.choice(options)
