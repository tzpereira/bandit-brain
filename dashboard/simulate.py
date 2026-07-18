"""Synthetic live-traffic generator backing the "Simulate live data" mode."""

import random

import polars as pl
from api_client import ingest_batch

DEVICES = ["desktop", "mobile", "tablet"]
LOCATIONS = ["USA", "CAN", "BRA", "FRA", "DEU"]
USER_SEGMENTS = ["new_user", "returning_user", "vip"]


def simulate_events(n_events, allocations_df, variants, experiment_name, date_selected, batch_size) -> bool:
    variant_list = (
        [row["variant_name"] for row in allocations_df.iter_rows(named=True)]
        if isinstance(allocations_df, pl.DataFrame) and allocations_df.height > 0
        else variants
    )
    if not variant_list:
        return False

    base_ctr = {v: random.uniform(0.04, 0.07) for v in variant_list}

    success = True
    events = []
    for _ in range(n_events):
        variant = random.choice(variant_list)
        device = random.choice(DEVICES)
        location = random.choice(LOCATIONS)
        segment = random.choice(USER_SEGMENTS)
        hour = random.randint(0, 23)
        ctr = base_ctr[variant]
        ctr *= 1.1 if device == "mobile" else 0.9 if device == "tablet" else 1.0
        ctr *= 1.5 if segment == "vip" else 0.8 if segment == "new_user" else 1.0
        ctr *= 1.2 if 18 <= hour <= 21 else 0.7 if 0 <= hour <= 6 else 1.0
        click = 1 if random.random() < ctr else 0
        base_cpc = 0.25 if click else 0.05
        cost = round(
            base_cpc
            * (1.2 if device == "mobile" else 0.9 if device == "tablet" else 1.0)
            * (1.5 if segment == "vip" else 0.8 if segment == "new_user" else 1.0)
            * (1.3 if location == "US" else 1.1 if location == "CA" else 0.7 if location == "BR" else 1.0),
            4,
        )

        events.append(
            {
                "experiment_name": experiment_name,
                "variant_name": variant,
                "impressions": 1,
                "clicks": click,
                "event_date": str(date_selected),
                "cost": cost,
                "context": {"device": device, "location": location, "user_segment": segment, "hour": hour},
            }
        )

        # Send in batches of batch_size
        if len(events) >= batch_size:
            if not ingest_batch(events):
                success = False
            events = []

    # Send any remaining events
    if events and not ingest_batch(events):
        success = False
    return success
