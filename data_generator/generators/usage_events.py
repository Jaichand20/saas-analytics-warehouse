import pandas as pd

FEATURES = ["dashboard", "reports", "api", "integrations", "exports", "search", "billing_admin"]


def generate_usage_events(rng, active_intervals, end_date, min_events_per_day=1, max_events_per_day=8):
    """Hourly-grain usage log for every active subscription window. Usage tapers
    off in the 30 days before a cancellation, giving the churn-risk-scoring
    queries a real signal to detect (not just synthetic noise).
    """
    events = []
    for account_id, intervals in active_intervals.items():
        for start, end in intervals:
            period_end = end if end is not None else end_date
            num_days = (period_end - start).days
            if num_days <= 0:
                continue

            taper_start = period_end - pd.Timedelta(days=30) if end is not None else None

            for day_offset in range(num_days):
                day = start + pd.Timedelta(days=day_offset)

                intensity = 1.0
                if taper_start is not None and day >= taper_start:
                    days_into_taper = (day - taper_start).days
                    intensity = max(0.1, 1.0 - days_into_taper / 30 * 0.85)

                base_count = rng.integers(min_events_per_day, max_events_per_day + 1)
                count = max(0, int(round(base_count * intensity)))
                num_users = int(rng.integers(1, 6))

                for _ in range(count):
                    hour = int(rng.integers(0, 24))
                    minute = int(rng.integers(0, 60))
                    ts = day + pd.Timedelta(hours=hour, minutes=minute)
                    events.append(
                        {
                            "account_id": account_id,
                            "user_id": f"{account_id}_u{int(rng.integers(0, num_users)):02d}",
                            "feature_name": rng.choice(FEATURES),
                            "event_timestamp": ts,
                            "usage_units": round(float(rng.gamma(2.0, 1.5)), 2),
                        }
                    )

    df = pd.DataFrame(events)
    df.insert(0, "event_id", [f"usage_{i:07d}" for i in range(len(df))])
    return df
