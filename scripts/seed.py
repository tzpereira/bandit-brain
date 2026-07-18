"""
Seed the local stack with a demo user and the example ads dataset.

Usage (with `docker compose up` running):
    uv run python scripts/seed.py

Environment:
    SEED_API_URL    API base URL (default: http://localhost:8000)
    SEED_EMAIL      demo account email (default: demo@banditbrain.dev)
    SEED_PASSWORD   demo account password. Defaults to "demo-password" only when
                    SEED_API_URL looks local; required (no fallback) otherwise, so a
                    publicly-known password can't accidentally end up protecting a
                    real deployment.
    SEED_SECRET     must match the API's DEMO_SEED_SECRET if the target account is
                    flagged is_demo (read-only) - otherwise /ingest returns 403.
                    Irrelevant for a normal (non-demo) account.
"""

import csv
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

API_URL = os.getenv("SEED_API_URL", "http://localhost:8000")
EMAIL = os.getenv("SEED_EMAIL", "demo@banditbrain.dev")
PASSWORD = os.getenv("SEED_PASSWORD")
SEED_SECRET = os.getenv("SEED_SECRET")
EXPERIMENT_NAME = "example_ads"
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "backend", "0.0.0.0")
CSV_PATH = Path(__file__).resolve().parent.parent / "public" / "example_ads_data.csv"
BATCH_SIZE = 200
DAYS_OF_HISTORY = 14


def get_token(client: httpx.Client, password: str) -> str:
    signup = client.post(f"{API_URL}/signup", json={"email": EMAIL, "password": password})
    if signup.status_code not in (200, 201, 400, 409):
        signup.raise_for_status()

    login = client.post(f"{API_URL}/login", json={"email": EMAIL, "password": password})
    login.raise_for_status()
    return login.json()["access_token"]


def load_events() -> list[dict]:
    events = []
    with CSV_PATH.open() as f:
        for i, row in enumerate(csv.DictReader(f)):
            # Spread rows across a rolling window of days so date filters have data.
            event_date = date.today() - timedelta(days=i % DAYS_OF_HISTORY)
            events.append(
                {
                    "experiment_name": EXPERIMENT_NAME,
                    "variant_name": row["variant_name"],
                    "impressions": int(row["impressions"]),
                    "clicks": int(row["clicks"]),
                    "cost": float(row["cost"]),
                    "event_date": event_date.isoformat(),
                    "context": {
                        "device": row["device"],
                        "location": row["location"],
                        "user_segment": row["user_segment"],
                        "hour": int(row["hour"]),
                    },
                }
            )
    return events


def resolve_password() -> str:
    if PASSWORD:
        return PASSWORD
    is_local = any(host in API_URL for host in _LOCAL_HOSTS)
    if is_local:
        return "demo-password"
    print(
        f"SEED_PASSWORD is not set and {API_URL!r} doesn't look local. Refusing to seed a "
        "non-local target with a publicly-known default password. Set SEED_PASSWORD explicitly.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def main() -> int:
    password = resolve_password()
    with httpx.Client(timeout=30) as client:
        try:
            token = get_token(client, password)
        except httpx.HTTPError as exc:
            print(f"Could not authenticate against {API_URL}: {exc}", file=sys.stderr)
            print("Is the stack running? Try: docker compose up -d", file=sys.stderr)
            return 1

        headers = {"Authorization": f"Bearer {token}"}
        if SEED_SECRET:
            headers["X-Seed-Secret"] = SEED_SECRET
        events = load_events()
        for start in range(0, len(events), BATCH_SIZE):
            batch = events[start : start + BATCH_SIZE]
            response = client.post(f"{API_URL}/ingest", json=batch, headers=headers)
            response.raise_for_status()
            print(f"Ingested {min(start + BATCH_SIZE, len(events))}/{len(events)} events")

    print(f"Done. Demo account: {EMAIL} / {password} — experiment '{EXPERIMENT_NAME}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
