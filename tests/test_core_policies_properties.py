"""
Property-based tests for the allocation invariants every BanditPolicy must hold,
regardless of the specific metrics fed in: allocations always form a valid
distribution, floors/caps are always respected, and deterministic policies never
change their answer just because the caller happened to list the variants in a
different order.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from banditbrain.core.models import Metric
from banditbrain.core.policies import EpsilonGreedyBandit, SoftmaxBandit, ThompsonSamplingBandit, UCBBandit

VARIANT_POOL = ["A", "B", "C", "D", "E"]


def make_metric(variant: str, impressions: int, clicks: int) -> Metric:
    ctr = clicks / impressions if impressions else 0.0
    return Metric(
        variant_name=variant,
        clicks=clicks,
        total_cost=1.0,
        impressions=impressions,
        device="mobile",
        location="BRA",
        user_segment="new_user",
        ctr=ctr,
        ctr_se=0.0,
        ctr_ci_lower=0.0,
        ctr_ci_upper=1.0,
    )


@st.composite
def metrics_strategy(draw, min_n: int = 2, max_n: int = 5) -> list[Metric]:
    n = draw(st.integers(min_value=min_n, max_value=max_n))
    metrics = []
    for name in VARIANT_POOL[:n]:
        impressions = draw(st.integers(min_value=0, max_value=100_000))
        clicks = draw(st.integers(min_value=0, max_value=impressions)) if impressions > 0 else 0
        metrics.append(make_metric(name, impressions, clicks))
    return metrics


DETERMINISTIC_FACTORIES = [
    lambda m: EpsilonGreedyBandit(m, epsilon=0.1),
    lambda m: UCBBandit(m, c=2.0),
    lambda m: SoftmaxBandit(m, tau=0.1),
]

ALL_FACTORIES = [
    *DETERMINISTIC_FACTORIES,
    lambda m: ThompsonSamplingBandit(m, seed=0, n_samples=2_000),
]


@settings(max_examples=50, deadline=None)
@given(metrics=metrics_strategy())
def test_allocate_is_always_a_valid_distribution(metrics):
    for factory in ALL_FACTORIES:
        probs = factory(metrics).allocate()
        assert probs.sum() == pytest.approx(1.0, abs=1e-6)
        assert all(-1e-9 <= p <= 1.0 + 1e-9 for p in probs)


@settings(max_examples=50, deadline=None)
@given(
    metrics=metrics_strategy(),
    floor=st.floats(min_value=0.0, max_value=0.3),
    cap_slack=st.floats(min_value=0.0, max_value=0.5),
)
def test_get_allocation_always_respects_floor_and_cap(metrics, floor, cap_slack):
    n = len(metrics)
    floor = min(floor, 1.0 / n)  # keep floors jointly feasible: floor * n <= 1
    cap = min(1.0, floor + cap_slack + 1.0 / n)  # keep caps jointly feasible: cap * n >= 1

    for factory in (
        lambda m: EpsilonGreedyBandit(m, epsilon=0.1, min_allocation=floor, max_allocation=cap),
        lambda m: SoftmaxBandit(m, tau=0.1, min_allocation=floor, max_allocation=cap),
    ):
        allocations = factory(metrics).get_allocation()
        pcts = [a.allocated_pct for a in allocations]
        assert sum(pcts) == pytest.approx(1.0, abs=1e-6)
        for p in pcts:
            assert p >= floor - 1e-6
            assert p <= cap + 1e-6


@settings(max_examples=50, deadline=None)
@given(metrics=metrics_strategy())
def test_deterministic_policies_are_permutation_equivariant(metrics):
    # Reordering the input variants must reorder the output the same way — a
    # policy's answer for "variant A" cannot depend on which position it's listed in.
    n = len(metrics)
    perm = list(reversed(range(n)))
    permuted_metrics = [metrics[i] for i in perm]

    for factory in DETERMINISTIC_FACTORIES:
        original = factory(metrics).allocate()
        permuted = factory(permuted_metrics).allocate()
        expected = np.array([original[i] for i in perm])
        np.testing.assert_allclose(permuted, expected, atol=1e-9)
