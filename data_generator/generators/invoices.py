import pandas as pd


def generate_invoices(rng, subscription_events_df, active_intervals, plans_df, end_date):
    """Monthly invoice per active subscription window, billed at the plan price
    in effect at that time. A small share are pending/failed (payment_date
    stays null), which feeds the churn-risk signal downstream.
    """
    plan_price = plans_df.set_index("plan_id")["list_price_usd"].to_dict()
    plan_interval = plans_df.set_index("plan_id")["billing_interval"].to_dict()

    events_by_account = {
        account_id: grp.sort_values("event_timestamp")
        for account_id, grp in subscription_events_df.groupby("account_id")
    }

    invoices = []
    for account_id, intervals in active_intervals.items():
        events = events_by_account[account_id]
        for start, end in intervals:
            period_end = end if end is not None else end_date
            cursor = start
            while cursor < period_end:
                plan_id = _plan_at(events, cursor)
                if plan_id is None:
                    cursor += pd.Timedelta(days=30)
                    continue

                amount = plan_price[plan_id] / 12 if plan_interval[plan_id] == "annual" else plan_price[plan_id]
                roll = rng.random()
                if roll < 0.03:
                    status, payment_date, amount_paid = "failed", None, 0.0
                elif roll < 0.08:
                    status, payment_date, amount_paid = "pending", None, 0.0
                else:
                    status = "paid"
                    payment_date = cursor + pd.Timedelta(days=int(rng.integers(0, 5)))
                    amount_paid = round(amount, 2)

                invoices.append(
                    {
                        "account_id": account_id,
                        "invoice_date": cursor,
                        "amount_due_usd": round(amount, 2),
                        "amount_paid_usd": amount_paid,
                        "status": status,
                        "payment_date": payment_date,
                    }
                )
                cursor += pd.Timedelta(days=30)

    df = pd.DataFrame(invoices)
    df.insert(0, "invoice_id", [f"inv_{i:06d}" for i in range(len(df))])
    return df


def _plan_at(events_sorted, ts):
    prior = events_sorted[events_sorted["event_timestamp"] <= ts]
    if prior.empty:
        return None
    return prior.iloc[-1]["plan_id"]
