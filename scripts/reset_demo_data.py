"""
Reset the demo account's data: wipe it, then re-seed from scratch.

Intended to run on a schedule (e.g. nightly) against a deployed demo instance,
so a public demo's data can't drift or accumulate garbage between visitors —
see ROADMAP.md Phase 4 guardrails. If the target account is flagged is_demo,
DELETE /experiments, DELETE /allocations, and POST /ingest are all guarded
against it (api/guardrails.py); SEED_SECRET must match the API's
DEMO_SEED_SECRET to get through.

Usage:
    uv run python scripts/reset_demo_data.py

Environment: same as scripts/seed.py (SEED_API_URL, SEED_EMAIL, SEED_PASSWORD,
SEED_SECRET).
"""

import sys

import httpx
from seed import API_URL, BATCH_SIZE, EMAIL, SEED_SECRET, get_token, load_events, resolve_password


def main() -> int:
    password = resolve_password()

    with httpx.Client(timeout=30) as client:
        try:
            token = get_token(client, password)
        except httpx.HTTPError as exc:
            print(f"Could not authenticate against {API_URL}: {exc}", file=sys.stderr)
            return 1

        headers = {"Authorization": f"Bearer {token}"}
        if SEED_SECRET:
            headers["X-Seed-Secret"] = SEED_SECRET

        for path in ("/allocations", "/experiments"):
            response = client.delete(f"{API_URL}{path}", headers=headers)
            if response.status_code not in (200, 204):
                print(f"Failed to clear {path}: {response.status_code} {response.text}", file=sys.stderr)
                return 1
            print(f"Cleared {path}")

        events = load_events()
        for start in range(0, len(events), BATCH_SIZE):
            batch = events[start : start + BATCH_SIZE]
            response = client.post(f"{API_URL}/ingest", json=batch, headers=headers)
            response.raise_for_status()
            print(f"Ingested {min(start + BATCH_SIZE, len(events))}/{len(events)} events")

    print(f"Demo data reset for {EMAIL}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
