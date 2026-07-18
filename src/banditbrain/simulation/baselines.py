"""
Baseline allocations to beat: what the four real policies (Phase 1) are being
compared against in simulation (Phase 2). Each returns a plain probability
vector over the arms — the same shape core.policies.BanditPolicy.allocate()
returns — so the simulation runner can drive baselines and real policies
through the identical loop.
"""

import numpy as np


def uniform_allocation(n_arms: int) -> np.ndarray:
    """A fixed A/B/n split: equal traffic to every arm, forever."""
    return np.full(n_arms, 1.0 / n_arms)


def oracle_allocation(n_arms: int, best_arm: int) -> np.ndarray:
    """
    The clairvoyant baseline: always plays the arm that's actually best. Only
    computable in simulation, where the ground truth is known — this is the
    ceiling every real policy is measured against, not a deployable policy.
    """
    probs = np.zeros(n_arms)
    probs[best_arm] = 1.0
    return probs


def fixed_split_allocation(n_arms: int, favored_arm: int = 0, favored_share: float = 0.9) -> np.ndarray:
    """A static, non-adaptive split (e.g. 90/10): favored_arm gets favored_share, the rest split evenly."""
    assert 0.0 <= favored_share <= 1.0, "favored_share must be in [0, 1]"
    assert n_arms >= 2, "need at least two arms"
    probs = np.full(n_arms, (1.0 - favored_share) / (n_arms - 1))
    probs[favored_arm] = favored_share
    return probs
