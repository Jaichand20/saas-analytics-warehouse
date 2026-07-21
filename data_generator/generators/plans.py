import pandas as pd

PLAN_DEFINITIONS = [
    {"plan_id": "starter", "plan_name": "Starter", "billing_interval": "monthly", "list_price_usd": 29.0, "tier_rank": 1},
    {"plan_id": "pro", "plan_name": "Pro", "billing_interval": "monthly", "list_price_usd": 99.0, "tier_rank": 2},
    {"plan_id": "business", "plan_name": "Business", "billing_interval": "monthly", "list_price_usd": 299.0, "tier_rank": 3},
    {"plan_id": "enterprise", "plan_name": "Enterprise", "billing_interval": "annual", "list_price_usd": 12000.0, "tier_rank": 4},
]


def generate_plans():
    return pd.DataFrame(PLAN_DEFINITIONS)
