import numpy as np
import pytest

from banditbrain.core.decide import sample_decision
from banditbrain.core.models import Allocation


def make_allocation(variant: str, pct: float) -> Allocation:
    return Allocation(
        experiment_name="exp",
        variant_name=variant,
        allocated_pct=pct,
        algorithm="ts",
        params={"n_samples": 10_000},
        date="2026-01-02",
    )


def test_sample_decision_returns_a_valid_variant_and_propensity():
    allocations = [make_allocation("A", 0.7), make_allocation("B", 0.3)]
    variant, propensity = sample_decision(allocations, rng=np.random.default_rng(0))
    assert variant in {"A", "B"}
    assert propensity in {0.7, 0.3}


def test_sample_decision_is_reproducible_given_a_seeded_rng():
    allocations = [make_allocation("A", 0.7), make_allocation("B", 0.3)]
    first = sample_decision(allocations, rng=np.random.default_rng(42))
    second = sample_decision(allocations, rng=np.random.default_rng(42))
    assert first == second


def test_sample_decision_matches_the_allocation_distribution_over_many_draws():
    allocations = [make_allocation("A", 0.8), make_allocation("B", 0.2)]
    rng = np.random.default_rng(0)
    draws = [sample_decision(allocations, rng=rng)[0] for _ in range(5_000)]
    share_a = draws.count("A") / len(draws)
    assert share_a == pytest.approx(0.8, abs=0.03)


def test_sample_decision_rejects_empty_allocations():
    with pytest.raises(ValueError, match="must not be empty"):
        sample_decision([])


def test_sample_decision_rejects_probabilities_not_summing_to_one():
    allocations = [make_allocation("A", 0.5), make_allocation("B", 0.2)]
    with pytest.raises(ValueError, match="must sum to 1"):
        sample_decision(allocations)


def test_sample_decision_never_picks_a_zero_probability_arm():
    allocations = [make_allocation("A", 1.0), make_allocation("B", 0.0)]
    rng = np.random.default_rng(0)
    for _ in range(200):
        variant, propensity = sample_decision(allocations, rng=rng)
        assert variant == "A"
        assert propensity == pytest.approx(1.0)
