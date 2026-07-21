import pandas as pd


def generate_subscription_events(rng, accounts_df, plans_df, end_date):
    """Simulates each account's subscription lifecycle (create/upgrade/downgrade/
    cancel/reactivate) from signup to end_date, roughly monthly cadence with jitter.
    """
    events = []
    plans_by_rank = plans_df.sort_values("tier_rank").reset_index(drop=True)
    weights = _tier_weights(len(plans_by_rank))

    for _, account in accounts_df.iterrows():
        account_id = account["account_id"]
        signup_date = account["signup_date"]

        current_rank_idx = rng.choice(len(plans_by_rank), p=weights)
        current_plan = plans_by_rank.iloc[current_rank_idx]
        mrr = _monthlyize(current_plan["list_price_usd"], current_plan["billing_interval"])

        events.append(_event(account_id, current_plan["plan_id"], "create", signup_date, mrr))

        cancelled = False
        cursor = signup_date
        while cursor < end_date and not cancelled:
            cursor = cursor + pd.Timedelta(days=int(rng.integers(20, 45)))
            if cursor >= end_date:
                break

            roll = rng.random()
            if roll < 0.05:
                events.append(_event(account_id, current_plan["plan_id"], "cancel", cursor, -mrr))
                cancelled = True
                if rng.random() < 0.2 and cursor + pd.Timedelta(days=30) < end_date:
                    reactivate_time = cursor + pd.Timedelta(days=int(rng.integers(15, 60)))
                    if reactivate_time < end_date:
                        events.append(
                            _event(account_id, current_plan["plan_id"], "reactivate", reactivate_time, mrr)
                        )
                        cancelled = False
                        cursor = reactivate_time
            elif roll < 0.15 and current_rank_idx < len(plans_by_rank) - 1:
                current_rank_idx += 1
                new_plan = plans_by_rank.iloc[current_rank_idx]
                new_mrr = _monthlyize(new_plan["list_price_usd"], new_plan["billing_interval"])
                events.append(_event(account_id, new_plan["plan_id"], "upgrade", cursor, new_mrr - mrr))
                current_plan, mrr = new_plan, new_mrr
            elif roll < 0.22 and current_rank_idx > 0:
                current_rank_idx -= 1
                new_plan = plans_by_rank.iloc[current_rank_idx]
                new_mrr = _monthlyize(new_plan["list_price_usd"], new_plan["billing_interval"])
                events.append(_event(account_id, new_plan["plan_id"], "downgrade", cursor, new_mrr - mrr))
                current_plan, mrr = new_plan, new_mrr

    df = pd.DataFrame(events)
    df.insert(0, "event_id", [f"sube_{i:06d}" for i in range(len(df))])
    return df


def build_active_intervals(subscription_events_df):
    """Per account, the (start, end) windows during which the subscription was
    active. end=None means still active as of the last generated event.
    """
    intervals = {}
    for account_id, grp in subscription_events_df.groupby("account_id"):
        grp = grp.sort_values("event_timestamp")
        current_start = None
        acct_intervals = []
        for _, row in grp.iterrows():
            if row["event_type"] in ("create", "reactivate"):
                current_start = row["event_timestamp"]
            elif row["event_type"] == "cancel" and current_start is not None:
                acct_intervals.append((current_start, row["event_timestamp"]))
                current_start = None
        if current_start is not None:
            acct_intervals.append((current_start, None))
        intervals[account_id] = acct_intervals
    return intervals


def _tier_weights(n):
    base_weights = [0.4, 0.3, 0.2, 0.1][:n]
    total = sum(base_weights)
    return [w / total for w in base_weights]


def _monthlyize(list_price, billing_interval):
    return list_price / 12 if billing_interval == "annual" else list_price


def _event(account_id, plan_id, event_type, event_timestamp, mrr_delta_usd):
    return {
        "account_id": account_id,
        "plan_id": plan_id,
        "event_type": event_type,
        "event_timestamp": event_timestamp,
        "mrr_delta_usd": round(mrr_delta_usd, 2),
    }
