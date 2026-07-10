import argparse
import random
import time
from datetime import datetime

import requests

# -----------------------------
# Experiment Configuration
# -----------------------------
EXPERIMENT_NAME = "AB_Test_Pages"
VARIANTS = ["Page_A", "Page_B", "Page_C"]

# Base Click-Through Rate (CTR) by Variant
BASE_CTR = {"Page_A": 0.05, "Page_B": 0.06, "Page_C": 0.04}

# Possible Contexts
DEVICES = ["desktop", "mobile", "tablet"]
LOCATIONS = ["USA", "CAN", "BRA", "FRA", "DEU"]
USER_SEGMENTS = ["new_user", "returning_user", "vip"]

parser = argparse.ArgumentParser(description="Streaming data simulator for MAB")
parser.add_argument("--max_events", type=int, default=None, help="Maximum number of events to send")
parser.add_argument("--batch_size", type=int, default=1, help="Batch size of events per request")
parser.add_argument("--interval", type=float, default=0.05, help="Interval between batches (seconds)")
parser.add_argument("--api_url", type=str, default="http://localhost:8000/ingest", help="Ingestion API URL")
args = parser.parse_args()

EVENT_INTERVAL = args.interval
API_URL = args.api_url
MAX_EVENTS = args.max_events
BATCH_SIZE = args.batch_size


# -----------------------------
# Function to simulate CTR with context
# -----------------------------
def simulate_click(variant, device, segment, hour):
    """
    Returns 1 if there was a click, 0 otherwise.
    CTR varies by variant, device, segment, and hour of the day.
    """
    ctr = BASE_CTR[variant]

    # Adjustment by device
    if device == "mobile":
        ctr *= 1.1
    elif device == "tablet":
        ctr *= 0.9

    # Adjustment by segment
    if segment == "vip":
        ctr *= 1.5
    elif segment == "new_user":
        ctr *= 0.8

    # Adjustment by hour of the day (peaks 18h-21h)
    if 18 <= hour <= 21:
        ctr *= 1.2
    elif 0 <= hour <= 6:
        ctr *= 0.7

    return 1 if random.random() < ctr else 0


# -----------------------------

# Event loop with stop option and batch
event_count = 0
headers = {"Content-Type": "application/json"}
while True:
    batch = []
    batch_time = datetime.now()
    # Uniformly distribute events across hours
    hours = [h for h in range(24)]
    hour_per_event = [hours[i % 24] for i in range(BATCH_SIZE)]
    for idx in range(BATCH_SIZE):
        if MAX_EVENTS is not None and event_count >= MAX_EVENTS:
            break
        variant = random.choice(VARIANTS)
        device = random.choice(DEVICES)
        location = random.choice(LOCATIONS)
        segment = random.choice(USER_SEGMENTS)
        hour = hour_per_event[idx]
        event_date = datetime.now().date().isoformat()
        impressions = 1
        clicks = simulate_click(variant, device, segment, hour)

        # Simulate a realistic cost per impression/click
        base_cpc = 0.25 if clicks else 0.05
        device_factor = 1.2 if device == "mobile" else (0.9 if device == "tablet" else 1.0)
        segment_factor = 1.5 if segment == "vip" else (0.8 if segment == "new_user" else 1.0)
        location_factor = (
            1.3 if location == "USA" else (1.1 if location == "CAN" else (0.7 if location == "BRA" else 1.0))
        )
        cost = round(base_cpc * device_factor * segment_factor * location_factor, 4)

        payload = {
            "experiment_name": EXPERIMENT_NAME,
            "variant_name": variant,
            "impressions": impressions,
            "clicks": clicks,
            "event_date": event_date,
            "cost": cost,
            "context": {"device": device, "location": location, "user_segment": segment, "hour": hour},
        }
        batch.append(payload)
        event_count += 1

    if not batch:
        break

    # Send batch to API
    try:
        # Always send as a list, even if batch_size == 1
        response = requests.post(API_URL, json=batch, headers=headers)
        if response.status_code == 200:
            print(f"[{batch_time}] Batch sent: {batch}")
        else:
            print(f"[{batch_time}] ERROR sending: {response.status_code} | Response: {response.text}")
    except Exception as e:
        print(f"[{batch_time}] EXCEPTION: {e}")

    if MAX_EVENTS is not None and event_count >= MAX_EVENTS:
        print(f"Simulation ended after {event_count} events.")
        break

    time.sleep(EVENT_INTERVAL)
