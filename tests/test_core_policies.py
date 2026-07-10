import numpy as np
import pytest

from banditbrain.core.models import Metric
from banditbrain.core.policies import (
    EpsilonGreedyBandit,
    SoftmaxBandit,
    ThompsonSamplingBandit,
    UCBBandit,
)


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
        ctr_se=0.01,
        ctr_ci_lower=max(ctr - 0.02, 0.0),
        ctr_ci_upper=ctr + 0.02,
    )


@pytest.fixture
def metrics() -> list[Metric]:
    return [
        make_metric("A", impressions=1000, clicks=120),
        make_metric("B", impressions=950, clicks=80),
        make_metric("C", impressions=500, clicks=60),
    ]


@pytest.mark.parametrize(
    ("bandit_factory", "algorithm"),
    [
        (lambda m: EpsilonGreedyBandit(m, epsilon=0.1, experiment_name="exp", date="2026-01-01"), "eg"),
        (lambda m: UCBBandit(m, c=2.0, experiment_name="exp", date="2026-01-01"), "ucb"),
        (lambda m: ThompsonSamplingBandit(m, experiment_name="exp", date="2026-01-01"), "ts"),
        (lambda m: SoftmaxBandit(m, tau=0.1, experiment_name="exp", date="2026-01-01"), "softmax"),
    ],
)
def test_policy_allocations_are_valid(metrics, bandit_factory, algorithm):
    allocations = bandit_factory(metrics).get_allocation()

    assert {a.variant_name for a in allocations} == {"A", "B", "C"}
    assert all(a.algorithm == algorithm for a in allocations)
    assert all(0.0 <= a.allocated_pct <= 1.0 for a in allocations)
    assert sum(a.allocated_pct for a in allocations) == pytest.approx(1.0)
    # Allocation is always a next-day forecast.
    assert all(a.date == "2026-01-02" for a in allocations)


def test_softmax_favors_better_variants(metrics):
    allocations = SoftmaxBandit(metrics, tau=0.1, experiment_name="exp", date="2026-01-01").get_allocation()
    by_variant = {a.variant_name: a.allocated_pct for a in allocations}
    # A (12% CTR) and C (12% CTR) should outrank B (~8.4% CTR).
    assert by_variant["A"] > by_variant["B"]
    assert by_variant["C"] > by_variant["B"]


def test_softmax_probabilities_are_numerically_stable():
    probs = SoftmaxBandit._softmax(np.array([1000.0, 1000.0, 1000.0]), tau=0.1)
    assert probs == pytest.approx([1 / 3, 1 / 3, 1 / 3])
