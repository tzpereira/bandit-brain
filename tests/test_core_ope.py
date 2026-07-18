import numpy as np
import pytest

from banditbrain.core.ope import (
    effective_sample_size,
    evaluate,
    importance_weights,
    ips_confidence_interval,
    ips_estimate,
    propensity_overlap,
    snips_confidence_interval,
    snips_estimate,
    trust_level,
)


def test_importance_weights_are_target_over_logging():
    w = importance_weights(logging_propensities=[0.5, 0.5], target_propensities=[0.8, 0.2])
    np.testing.assert_allclose(w, [1.6, 0.4])


def test_importance_weights_reject_zero_logging_propensity():
    with pytest.raises(ValueError, match="must be > 0"):
        importance_weights(logging_propensities=[0.5, 0.0], target_propensities=[0.8, 0.2])


# Hand-computable case: logging is uniform (0.5/0.5) over two logged decisions
# each of A and B; target favors A at 0.8, B at 0.2. w = [1.6, 1.6, 0.4, 0.4].
REWARDS = [1, 0, 1, 0]
LOGGING_PROPENSITIES = [0.5, 0.5, 0.5, 0.5]
TARGET_PROPENSITIES = [0.8, 0.8, 0.2, 0.2]


def test_ips_matches_hand_computed_value():
    # mean(w * r) = mean([1.6, 0, 0.4, 0]) = 2.0 / 4 = 0.5
    assert ips_estimate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES) == pytest.approx(0.5)


def test_snips_matches_hand_computed_value():
    # sum(w*r)/sum(w) = 2.0 / 4.0 = 0.5 (weights happen to sum to n here)
    assert snips_estimate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES) == pytest.approx(0.5)


def test_ips_and_snips_reduce_to_the_empirical_mean_when_target_equals_logging():
    rewards = [1, 0, 1, 1, 0]
    propensities = [0.3, 0.3, 0.3, 0.3, 0.3]
    assert ips_estimate(rewards, propensities, propensities) == pytest.approx(np.mean(rewards))
    assert snips_estimate(rewards, propensities, propensities) == pytest.approx(np.mean(rewards))


def test_ips_confidence_interval_contains_the_point_estimate():
    lower, upper = ips_confidence_interval(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES)
    estimate = ips_estimate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES)
    assert lower <= estimate <= upper


def test_snips_confidence_interval_contains_the_point_estimate():
    rng = np.random.default_rng(0)
    lower, upper = snips_confidence_interval(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES, rng=rng)
    estimate = snips_estimate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES)
    assert lower <= estimate <= upper


def test_effective_sample_size_equals_n_when_target_equals_logging():
    propensities = [0.3, 0.3, 0.3, 0.3, 0.3]
    ess = effective_sample_size(propensities, propensities)
    assert ess == pytest.approx(5.0)


def test_effective_sample_size_drops_with_extreme_weights():
    # One decision with a huge importance weight dominates -> ESS collapses well below n.
    logging_p = [0.5, 0.5, 0.5]
    target_p = [0.01, 0.01, 0.98]
    ess = effective_sample_size(logging_p, target_p)
    assert ess < 3.0


def test_propensity_overlap_reports_max_weight_and_ess_ratio():
    propensities = [0.3, 0.3, 0.3]
    diag = propensity_overlap(propensities, propensities)
    assert diag["max_importance_weight"] == pytest.approx(1.0)
    assert diag["effective_sample_ratio"] == pytest.approx(1.0)
    assert diag["n"] == 3


@pytest.mark.parametrize(
    ("sources", "expected"),
    [
        (["served", "served"], "audit-grade"),
        (["served", "byo"], "best-effort"),
        (["byo"], "best-effort"),
        (["unlabeled"], "best-effort"),
        ([], "best-effort"),
    ],
)
def test_trust_level_downgrades_on_any_non_served_source(sources, expected):
    assert trust_level(sources) == expected


def test_evaluate_returns_a_complete_result_with_snips_by_default():
    result = evaluate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES, decision_sources=["served"] * 4)
    assert result["estimator"] == "snips"
    assert result["estimate"] == pytest.approx(0.5)
    assert result["ci_lower"] <= result["estimate"] <= result["ci_upper"]
    assert result["trust_level"] == "audit-grade"
    assert result["n"] == 4


def test_evaluate_downgrades_trust_without_decision_sources():
    result = evaluate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES)
    assert result["trust_level"] == "best-effort"


def test_evaluate_supports_ips_estimator():
    result = evaluate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES, estimator="ips")
    assert result["estimator"] == "ips"
    assert result["estimate"] == pytest.approx(0.5)


def test_evaluate_rejects_unknown_estimator():
    with pytest.raises(ValueError, match="estimator must be"):
        evaluate(REWARDS, LOGGING_PROPENSITIES, TARGET_PROPENSITIES, estimator="bogus")


def test_ips_and_snips_recover_a_known_value_at_large_sample_size():
    # Logging uniform over 2 arms with known Bernoulli CTRs; target = always arm A.
    # True value of "always A" = true_ctr[A].
    rng = np.random.default_rng(0)
    true_ctrs = [0.3, 0.6]
    n = 200_000
    chosen = rng.integers(0, 2, size=n)  # uniform logging policy
    rewards = (rng.random(n) < np.array(true_ctrs)[chosen]).astype(float)
    logging_propensities = np.full(n, 0.5)
    target_propensities = (chosen == 0).astype(float)  # target puts 100% on arm A

    ips = ips_estimate(rewards, logging_propensities, target_propensities)
    snips = snips_estimate(rewards, logging_propensities, target_propensities)
    assert ips == pytest.approx(true_ctrs[0], abs=0.01)
    assert snips == pytest.approx(true_ctrs[0], abs=0.01)
