"""
Sampling a single decision from a stored allocation.

This is the "Rank" half of the serve -> log -> learn loop (see ROADMAP Phase 1.2):
a BanditPolicy.get_allocation() computes a batch distribution over arms once; this
module samples one arm per request from that stored distribution and reports the
propensity P(arm | state) needed to replay or off-policy-evaluate the decision later.
"""

import numpy as np

from banditbrain.core.models import Allocation


def sample_decision(allocations: list[Allocation], rng: np.random.Generator | None = None) -> tuple[str, float]:
    """
    Sample a variant from an allocation distribution.

    Args:
        allocations: the full batch of Allocation rows for one experiment/algorithm/date
            (as produced by BanditPolicy.get_allocation()); their allocated_pct values
            must sum to 1.
        rng: optional seeded generator for reproducible sampling; defaults to fresh entropy.

    Returns:
        (variant_name, propensity) — propensity is the allocated_pct of the chosen arm.
    """
    if not allocations:
        raise ValueError("allocations must not be empty")

    probs = np.array([a.allocated_pct for a in allocations], dtype=float)
    total = probs.sum()
    if not np.isclose(total, 1.0, atol=1e-6):
        raise ValueError(f"allocation probabilities must sum to 1 (got {total})")
    probs = probs / total  # normalize away float drift so np.random.Generator.choice accepts it

    rng = rng if rng is not None else np.random.default_rng()
    idx = int(rng.choice(len(allocations), p=probs))
    return allocations[idx].variant_name, float(probs[idx])
