"""
Shared demo configuration for the headline report (scripts/simulation_report.py)
and figures (scripts/generate_figures.py), so both always show the same numbers
computed the same way — one source of truth, not two scripts that could drift.

Uses the same true CTRs as the seeded example_ads dataset
(scripts/generate_example_data.py) so the simulation's story matches the demo's.
"""

import numpy as np

from banditbrain.core.policies import EpsilonGreedyBandit, SoftmaxBandit, ThompsonSamplingBandit, UCBBandit
from banditbrain.simulation.baselines import fixed_split_allocation, oracle_allocation, uniform_allocation
from banditbrain.simulation.runner import run_many_seeds

TRUE_CTRS = [0.030, 0.055, 0.038]  # A, B, C — matches scripts/generate_example_data.py
VARIANT_NAMES = ["A", "B", "C"]
HORIZON = 3_000
N_SEEDS = 50
TS_N_SAMPLES = 1_000  # fewer than production's 10k default; plenty for a regret comparison

BASELINE_NAME = "uniform A/B/C"
REAL_POLICY_NAMES = ["epsilon-greedy", "ucb", "thompson sampling", "softmax"]


def uniform_factory(metrics, rng):
    return uniform_allocation(len(metrics))


def oracle_factory(best_arm):
    def factory(metrics, rng):
        return oracle_allocation(len(metrics), best_arm)

    return factory


def fixed_90_10_factory(metrics, rng):
    return fixed_split_allocation(len(metrics), favored_arm=0, favored_share=0.9)


def eg_factory(metrics, rng):
    return EpsilonGreedyBandit(metrics, epsilon=0.1).allocate()


def ucb_factory(metrics, rng):
    return UCBBandit(metrics, c=2.0).allocate()


def ts_factory(metrics, rng):
    return ThompsonSamplingBandit(metrics, n_samples=TS_N_SAMPLES, seed=int(rng.integers(0, 2**32))).allocate()


def softmax_factory(metrics, rng):
    return SoftmaxBandit(metrics, tau=0.02).allocate()


def policy_factories() -> dict:
    """All policies + baselines compared in the demo, in report/figure display order."""
    best_arm = int(np.argmax(TRUE_CTRS))
    return {
        BASELINE_NAME: uniform_factory,
        "fixed 90/10": fixed_90_10_factory,
        "epsilon-greedy": eg_factory,
        "ucb": ucb_factory,
        "thompson sampling": ts_factory,
        "softmax": softmax_factory,
        "oracle (ceiling)": oracle_factory(best_arm),
    }


def run_all_policies(horizon: int = HORIZON, n_seeds: int = N_SEEDS) -> dict:
    """Run every policy/baseline once via run_many_seeds; returns results keyed by name."""
    return {name: run_many_seeds(factory, TRUE_CTRS, horizon, n_seeds) for name, factory in policy_factories().items()}
