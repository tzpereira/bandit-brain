"""
Synthetic Bernoulli-arm environment with known ground truth.

This is what lets Phase 2 *prove* the policies and the OPE estimators work,
rather than merely asserting it: every arm has a fixed true click-through rate,
so "how much better is this policy than uniform A/B" and "does this OPE estimate
match reality" both have a checkable right answer.
"""

import numpy as np


class BernoulliBanditEnv:
    """
    Arm ``i`` returns a ``Bernoulli(true_ctrs[i])`` reward when pulled. Seedable
    for reproducible simulation runs.
    """

    def __init__(self, true_ctrs: list[float], seed: int | None = None):
        assert len(true_ctrs) >= 2, "need at least two arms"
        assert all(0.0 <= p <= 1.0 for p in true_ctrs), "true_ctrs must be probabilities"
        self.true_ctrs = list(true_ctrs)
        self.n_arms = len(true_ctrs)
        self.rng = np.random.default_rng(seed)

    @property
    def best_arm(self) -> int:
        return int(np.argmax(self.true_ctrs))

    @property
    def best_ctr(self) -> float:
        return float(max(self.true_ctrs))

    def pull(self, arm: int) -> int:
        """Draw one Bernoulli reward (0 or 1) from the given arm's true CTR."""
        return int(self.rng.random() < self.true_ctrs[arm])
