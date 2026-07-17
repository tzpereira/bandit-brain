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
        (lambda m: ThompsonSamplingBandit(m, experiment_name="exp", date="2026-01-01", seed=0), "ts"),
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
    # Every allocation batch carries the policy params it was computed with, so a
    # served decision sampled from it can be replayed against the exact same policy version.
    assert all(a.params is not None for a in allocations)


@pytest.mark.parametrize(
    "bandit_factory",
    [
        lambda m: EpsilonGreedyBandit(m, epsilon=0.1),
        lambda m: UCBBandit(m, c=2.0),
        lambda m: ThompsonSamplingBandit(m, seed=0),
        lambda m: SoftmaxBandit(m, tau=0.1),
    ],
)
def test_allocations_are_fractional_not_all_or_nothing(metrics, bandit_factory):
    # Every policy must split traffic across more than one variant, not hand 100%
    # to a single winner.
    probs = bandit_factory(metrics).allocate()
    assert np.count_nonzero(probs) > 1


def test_epsilon_greedy_distribution():
    # A has a uniquely highest CTR (15%); it gets (1 - eps) + eps/K, the rest eps/K.
    m = [make_metric("A", 1000, 150), make_metric("B", 1000, 80), make_metric("C", 1000, 60)]
    probs = EpsilonGreedyBandit(m, epsilon=0.15).allocate()
    k = len(m)
    by_variant = dict(zip(["A", "B", "C"], probs, strict=True))
    assert by_variant["A"] == pytest.approx(0.85 + 0.15 / k)
    assert by_variant["B"] == pytest.approx(0.15 / k)
    assert by_variant["C"] == pytest.approx(0.15 / k)


def test_epsilon_greedy_ties_split_exploitation_mass():
    tied = [make_metric("A", 1000, 100), make_metric("B", 1000, 100), make_metric("C", 1000, 50)]
    probs = EpsilonGreedyBandit(tied, epsilon=0.2).allocate()
    by_variant = dict(zip(["A", "B", "C"], probs, strict=True))
    # A and B tie for best: each gets half of (1 - eps) plus its eps/K share.
    assert by_variant["A"] == pytest.approx(0.8 / 2 + 0.2 / 3)
    assert by_variant["A"] == pytest.approx(by_variant["B"])
    assert by_variant["C"] == pytest.approx(0.2 / 3)


def test_ucb_prioritises_unexplored_arms():
    m = [make_metric("A", 1000, 120), make_metric("B", 0, 0)]
    probs = UCBBandit(m, c=2.0, exploration_floor=0.1).allocate()
    by_variant = dict(zip(["A", "B"], probs, strict=True))
    # B has never been shown -> infinite optimistic score -> gets the top-arm mass.
    assert by_variant["B"] == pytest.approx(0.9 + 0.1 / 2)
    assert by_variant["A"] == pytest.approx(0.1 / 2)


def test_thompson_allocates_proportional_to_prob_best(metrics):
    probs = ThompsonSamplingBandit(metrics, seed=0).allocate()
    by_variant = dict(zip(["A", "B", "C"], probs, strict=True))
    # A (12%) and C (12%) both beat B (~8.4%); B should get the least mass.
    assert by_variant["A"] > by_variant["B"]
    assert by_variant["C"] > by_variant["B"]


def test_thompson_overwhelming_evidence_concentrates_on_winner():
    m = [make_metric("A", 100_000, 50_000), make_metric("B", 100_000, 1_000)]
    probs = ThompsonSamplingBandit(m, seed=0).allocate()
    by_variant = dict(zip(["A", "B"], probs, strict=True))
    assert by_variant["A"] > 0.99


def test_thompson_symmetric_arms_are_near_uniform():
    m = [make_metric("A", 1000, 100), make_metric("B", 1000, 100)]
    probs = ThompsonSamplingBandit(m, seed=0).allocate()
    assert probs == pytest.approx([0.5, 0.5], abs=0.05)


def test_thompson_is_reproducible_given_a_seed(metrics):
    first = ThompsonSamplingBandit(metrics, seed=42).allocate()
    second = ThompsonSamplingBandit(metrics, seed=42).allocate()
    np.testing.assert_array_equal(first, second)


def test_thompson_informative_prior_lets_a_known_good_arm_start_strong():
    # Both arms are brand new (zero data this experiment); without an informative
    # prior they'd split ~50/50. Seeding C's prior from a strong history (80% CTR,
    # high confidence) should make it dominate despite having no current-experiment data.
    m = [make_metric("A", 0, 0), make_metric("C", 0, 0)]
    flat = ThompsonSamplingBandit(m, seed=0).allocate()
    assert flat == pytest.approx([0.5, 0.5], abs=0.05)

    # C ~ Beta(800, 200) is tightly concentrated around 0.8; A stays uninformative
    # Beta(1, 1) (uniform on [0, 1]), so P(C > A) ~ 0.8 — a strong tilt from 50/50.
    informed = ThompsonSamplingBandit(m, seed=0, priors={"C": (800.0, 200.0)}).allocate()
    by_variant = dict(zip(["A", "C"], informed, strict=True))
    assert by_variant["C"] == pytest.approx(0.8, abs=0.03)


def test_thompson_prior_rejects_non_positive_parameters():
    m = [make_metric("A", 100, 10), make_metric("B", 100, 5)]
    with pytest.raises(AssertionError, match="alpha > 0 and beta > 0"):
        ThompsonSamplingBandit(m, priors={"A": (0.0, 1.0)})


def test_thompson_params_include_priors_for_replay():
    m = [make_metric("A", 100, 10), make_metric("B", 100, 5)]
    bandit = ThompsonSamplingBandit(m, priors={"A": (5.0, 2.0)})
    assert bandit.params() == {"n_samples": 10_000, "priors": {"A": (5.0, 2.0)}}


def test_softmax_favors_better_variants(metrics):
    allocations = SoftmaxBandit(metrics, tau=0.1, experiment_name="exp", date="2026-01-01").get_allocation()
    by_variant = {a.variant_name: a.allocated_pct for a in allocations}
    # A (12% CTR) and C (12% CTR) should outrank B (~8.4% CTR).
    assert by_variant["A"] > by_variant["B"]
    assert by_variant["C"] > by_variant["B"]


def test_softmax_probabilities_are_numerically_stable():
    probs = SoftmaxBandit._softmax(np.array([1000.0, 1000.0, 1000.0]), tau=0.1)
    assert probs == pytest.approx([1 / 3, 1 / 3, 1 / 3])
