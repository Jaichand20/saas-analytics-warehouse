import pandas as pd

INDUSTRIES = ["SaaS", "Fintech", "Healthcare", "Retail", "Manufacturing", "Media", "Education", "Logistics"]
EMPLOYEE_BANDS = ["1-10", "11-50", "51-200", "201-1000", "1000+"]
COUNTRIES = ["United States", "United Kingdom", "Germany", "Canada", "Australia", "India", "Netherlands", "France"]


def generate_accounts(rng, faker, num_accounts, start_date, end_date):
    """Generates accounts with a parent/child hierarchy: ~8% are enterprise
    umbrella accounts with 1-4 sub-accounts, some of which have their own
    children (depth 3), so downstream MRR rollups need a recursive CTE.
    """
    account_ids = [f"acct_{i:05d}" for i in range(num_accounts)]

    num_umbrellas = max(1, int(num_accounts * 0.08))
    umbrella_ids = account_ids[:num_umbrellas]
    remaining_ids = account_ids[num_umbrellas:]

    parent_map = {aid: None for aid in account_ids}
    idx = 0
    for umbrella_id in umbrella_ids:
        num_children = rng.integers(1, 5)
        for _ in range(num_children):
            if idx >= len(remaining_ids):
                break
            child_id = remaining_ids[idx]
            parent_map[child_id] = umbrella_id
            idx += 1
            if rng.random() < 0.3:
                num_grandchildren = rng.integers(1, 3)
                for _ in range(num_grandchildren):
                    if idx >= len(remaining_ids):
                        break
                    grandchild_id = remaining_ids[idx]
                    parent_map[grandchild_id] = child_id
                    idx += 1

    date_range_days = (end_date - start_date).days
    rows = []
    for aid in account_ids:
        signup_offset = rng.integers(0, max(date_range_days - 30, 1))
        signup_date = start_date + pd.Timedelta(days=int(signup_offset))
        rows.append(
            {
                "account_id": aid,
                "parent_account_id": parent_map[aid],
                "company_name": faker.company(),
                "industry": rng.choice(INDUSTRIES),
                "country": rng.choice(COUNTRIES),
                "signup_date": signup_date,
                "employee_count_band": rng.choice(EMPLOYEE_BANDS),
            }
        )
    return pd.DataFrame(rows)
