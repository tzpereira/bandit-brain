import pytest

from banditbrain.simulation.validate_ope import check_ope_coverage, true_value_of_fixed_policy


def test_true_value_is_the_dot_product_of_probs_and_ctrs():
    value = true_value_of_fixed_policy(true_ctrs=[0.2, 0.8], target_probs=[0.3, 0.7])
    assert value == pytest.approx(0.2 * 0.3 + 0.8 * 0.7)


def test_ips_coverage_is_close_to_95_percent_with_good_overlap():
    result = check_ope_coverage(
        true_ctrs=[0.3, 0.5],
        logging_probs=[0.5, 0.5],
        target_probs=[0.7, 0.3],
        n_logged=2000,
        n_trials=200,
        estimator="ips",
        seed=0,
    )
    assert abs(result["mean_bias"]) < 0.02
    assert 0.85 <= result["coverage_rate"] <= 1.0


def test_snips_coverage_is_close_to_95_percent_with_good_overlap():
    result = check_ope_coverage(
        true_ctrs=[0.3, 0.5],
        logging_probs=[0.5, 0.5],
        target_probs=[0.7, 0.3],
        n_logged=2000,
        n_trials=100,
        estimator="snips",
        seed=0,
        n_bootstrap=200,
    )
    assert abs(result["mean_bias"]) < 0.02
    assert 0.85 <= result["coverage_rate"] <= 1.0


def test_rejects_unknown_estimator():
    with pytest.raises(ValueError, match="estimator must be"):
        check_ope_coverage(
            true_ctrs=[0.3, 0.5],
            logging_probs=[0.5, 0.5],
            target_probs=[0.5, 0.5],
            n_logged=100,
            n_trials=5,
            estimator="bogus",
        )
