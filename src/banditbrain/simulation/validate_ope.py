"""
Validate the OPE estimators (core.ope) against known ground truth.

This is the crux of Phase 2: an estimator can look plausible and still be
wrong. Here, because BernoulliBanditEnv's true CTRs are known, the true value
of any *fixed* target policy is computable directly (a weighted average of the
true CTRs), so IPS/SNIPS estimates from logged data can be checked against
reality instead of trusted on faith — bias should be ~0, and a 95% CI should
actually contain the truth ~95% of the time across repeated trials.
"""

import numpy as np

from banditbrain.core.ope import (
    ips_confidence_interval,
    ips_estimate,
    snips_confidence_interval,
    snips_estimate,
)


def true_value_of_fixed_policy(true_ctrs: list[float], target_probs: list[float]) -> float:
    """The exact expected reward of a policy that plays a fixed distribution over arms forever."""
    return float(np.dot(target_probs, true_ctrs))


def check_ope_coverage(
    true_ctrs: list[float],
    logging_probs: list[float],
    target_probs: list[float],
    n_logged: int,
    n_trials: int,
    estimator: str = "snips",
    seed: int = 0,
    n_bootstrap: int = 300,
) -> dict:
    """
    Repeat `n_trials` times: log `n_logged` decisions under `logging_probs`,
    evaluate `target_probs` via IPS or SNIPS, and check whether the true value
    (known exactly, since true_ctrs is ground truth) falls inside the reported
    95% CI. Returns the empirical coverage rate and mean bias — a correctly
    calibrated 95% CI should cover the truth in ~95% of trials.
    """
    if estimator not in ("ips", "snips"):
        raise ValueError(f"estimator must be 'ips' or 'snips', got {estimator!r}")

    rng = np.random.default_rng(seed)
    true_value = true_value_of_fixed_policy(true_ctrs, target_probs)
    true_ctrs_arr = np.array(true_ctrs)
    logging_probs_arr = np.array(logging_probs)
    target_probs_arr = np.array(target_probs)
    n_arms = len(true_ctrs)

    covered = 0
    biases = np.empty(n_trials)

    for i in range(n_trials):
        arms = rng.choice(n_arms, size=n_logged, p=logging_probs_arr)
        rewards = (rng.random(n_logged) < true_ctrs_arr[arms]).astype(float)
        logging_propensities = logging_probs_arr[arms]
        target_propensities = target_probs_arr[arms]

        if estimator == "ips":
            estimate = ips_estimate(rewards, logging_propensities, target_propensities)
            ci_lower, ci_upper = ips_confidence_interval(rewards, logging_propensities, target_propensities)
        else:
            estimate = snips_estimate(rewards, logging_propensities, target_propensities)
            ci_lower, ci_upper = snips_confidence_interval(
                rewards, logging_propensities, target_propensities, rng=rng, n_bootstrap=n_bootstrap
            )

        biases[i] = estimate - true_value
        if ci_lower <= true_value <= ci_upper:
            covered += 1

    return {
        "estimator": estimator,
        "true_value": true_value,
        "mean_bias": float(biases.mean()),
        "coverage_rate": covered / n_trials,
        "n_trials": n_trials,
        "n_logged": n_logged,
    }
