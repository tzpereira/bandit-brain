"""
Generate a realistic, deterministic example ads dataset.

Unlike a naive random dump, this produces data with the properties a
Multi-Armed Bandit demo actually needs:

* clicks are drawn from Binomial(impressions, ctr), so clicks <= impressions
  always holds (CTR is a real probability in [0, 1]);
* CTRs sit in a believable 1-8% ad range;
* variant B is a genuine winner, so the bandits have a signal to find;
* context (device, user_segment, hour) shifts CTR multiplicatively, so the
  contextual analyses in the dashboard show real structure.

Deterministic: a fixed seed makes the output reproducible.

Usage:
    uv run python scripts/generate_example_data.py
"""

from pathlib import Path

import numpy as np

OUT_PATH = Path(__file__).resolve().parent.parent / "public" / "example_ads_data.csv"
SEED = 42
N_ROWS = 1000

VARIANTS = ["A", "B", "C"]
# "True" base CTR per variant. B is the winner; A and C are close to each other.
BASE_CTR = {"A": 0.030, "B": 0.055, "C": 0.038}

DEVICES = ["mobile", "desktop", "tablet"]
DEVICE_MULT = {"mobile": 1.15, "desktop": 1.0, "tablet": 0.85}

LOCATIONS = ["BRA", "USA", "CAN", "DEU", "GBR"]

SEGMENTS = ["new_user", "returning_user", "vip", "free"]
SEGMENT_MULT = {"new_user": 0.8, "returning_user": 1.0, "vip": 1.5, "free": 0.9}


def hour_mult(hour: int) -> float:
    # Evening peak (18-21h), overnight trough (0-6h).
    if 18 <= hour <= 21:
        return 1.25
    if 0 <= hour <= 6:
        return 0.7
    return 1.0


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []
    for _ in range(N_ROWS):
        variant = rng.choice(VARIANTS)
        device = rng.choice(DEVICES)
        location = rng.choice(LOCATIONS)
        segment = rng.choice(SEGMENTS)
        hour = int(rng.integers(0, 24))

        ctr = BASE_CTR[variant] * DEVICE_MULT[device] * SEGMENT_MULT[segment] * hour_mult(hour)
        ctr = float(np.clip(ctr, 0.0, 1.0))

        impressions = int(rng.integers(500, 5000))
        clicks = int(rng.binomial(impressions, ctr))
        # Cost per impression ~ $0.001-0.003, with mild noise.
        cost = round(impressions * rng.uniform(0.001, 0.003), 2)

        rows.append((variant, impressions, clicks, cost, device, location, segment, hour))

    rows.sort(key=lambda r: (r[0], r[4], r[6]))

    header = "variant_name,impressions,clicks,cost,device,location,user_segment,hour"
    lines = [header]
    lines += [",".join(str(v) for v in r) for r in rows]
    OUT_PATH.write_text("\n".join(lines) + "\n")

    # Report aggregate CTR per variant so the signal is visible.
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    for v in VARIANTS:
        vr = [r for r in rows if r[0] == v]
        imp = sum(r[1] for r in vr)
        clk = sum(r[2] for r in vr)
        print(f"  {v}: impressions={imp:>8} clicks={clk:>7} CTR={clk / imp:.4f}")


if __name__ == "__main__":
    main()
