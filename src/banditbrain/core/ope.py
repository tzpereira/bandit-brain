"""
Off-policy evaluation (OPE): estimate the value of a *target* policy from data
logged under a different *logging* policy, using each logged decision's
propensity — the counterfactual "what if we'd served differently" estimate a
bandit needs before promoting a challenger (see ROADMAP Phase 2).

Two estimators (Li et al., 2011's inverse propensity scoring, and its
self-normalized variant):

- **IPS** re-weights each logged reward by ``target_propensity / logging_propensity``
  and averages. Unbiased whenever every action the target policy might take has a
  nonzero logging propensity, but variance blows up when the two policies diverge.
- **SNIPS** normalizes by the sum of importance weights instead of by ``n``,
  trading a little bias for much lower variance — the standard practical default.

Both take parallel arrays: for each logged decision, the observed reward, the
propensity the *logging* policy assigned to the action actually taken, and the
propensity the *target* policy would assign to that same action.
"""

import numpy as np

DEFAULT_Z = 1.96
DEFAULT_CONFIDENCE = 0.95
DEFAULT_N_BOOTSTRAP = 2_000

# decision_source values that carry a known-correct propensity (see core.models.Decision).
TRUSTED_SOURCES = {"served"}


def importance_weights(logging_propensities, target_propensities) -> np.ndarray:
    """``target_propensity / logging_propensity`` per logged decision."""
    logging_propensities = np.asarray(logging_propensities, dtype=float)
    target_propensities = np.asarray(target_propensities, dtype=float)
    if np.any(logging_propensities <= 0):
        raise ValueError(
            "logging_propensities must be > 0 for every logged decision "
            "(a zero-propensity action could never have been logged)"
        )
    return target_propensities / logging_propensities


def ips_estimate(rewards, logging_propensities, target_propensities) -> float:
    """Inverse propensity scoring estimate of the target policy's average reward."""
    w = importance_weights(logging_propensities, target_propensities)
    rewards = np.asarray(rewards, dtype=float)
    return float(np.mean(w * rewards))


def snips_estimate(rewards, logging_propensities, target_propensities) -> float:
    """Self-normalized IPS: divides by sum(weights) instead of n."""
    w = importance_weights(logging_propensities, target_propensities)
    rewards = np.asarray(rewards, dtype=float)
    denom = w.sum()
    if denom <= 0:
        return 0.0
    return float((w * rewards).sum() / denom)


def ips_confidence_interval(
    rewards, logging_propensities, target_propensities, z: float = DEFAULT_Z
) -> tuple[float, float]:
    """Normal-approximation CI for IPS (a plain sample mean of weighted rewards)."""
    w = importance_weights(logging_propensities, target_propensities)
    rewards = np.asarray(rewards, dtype=float)
    n = len(rewards)
    weighted = w * rewards
    mean = float(weighted.mean())
    if n <= 1:
        return mean, mean
    se = float(weighted.std(ddof=1) / np.sqrt(n))
    return mean - z * se, mean + z * se


def snips_confidence_interval(
    rewards,
    logging_propensities,
    target_propensities,
    confidence: float = DEFAULT_CONFIDENCE,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    """
    Bootstrap percentile CI for SNIPS. SNIPS is a ratio estimator (sum / sum of
    weights) with no simple closed-form variance, so we resample logged decisions
    with replacement, recompute SNIPS each time, and take percentiles of the
    resulting distribution.
    """
    rng = rng if rng is not None else np.random.default_rng()
    rewards = np.asarray(rewards, dtype=float)
    logging_propensities = np.asarray(logging_propensities, dtype=float)
    target_propensities = np.asarray(target_propensities, dtype=float)
    n = len(rewards)
    if n == 0:
        return 0.0, 0.0

    estimates = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        estimates[i] = snips_estimate(rewards[idx], logging_propensities[idx], target_propensities[idx])

    alpha = 1.0 - confidence
    lower, upper = np.percentile(estimates, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lower), float(upper)


def effective_sample_size(logging_propensities, target_propensities) -> float:
    """
    Kish's effective sample size for importance-weighted estimates:
    ``(sum w)^2 / sum(w^2)``. Equals n when target == logging (no reweighting);
    drops toward 0 as a handful of extreme weights dominate the estimate — a
    reliability diagnostic, not just the raw sample count.
    """
    w = importance_weights(logging_propensities, target_propensities)
    denom = float(np.sum(w**2))
    if denom <= 0:
        return 0.0
    return float(np.sum(w) ** 2 / denom)


def propensity_overlap(logging_propensities, target_propensities) -> dict:
    """
    Reliability diagnostics for how much the target policy's action distribution
    overlaps the logging policy's. Poor overlap means the OPE estimate is
    extrapolating into logging-policy regions with little data and should not be
    trusted at face value, even though the estimator itself stays unbiased.
    """
    w = importance_weights(logging_propensities, target_propensities)
    n = len(w)
    ess = effective_sample_size(logging_propensities, target_propensities)
    return {
        "n": n,
        "effective_sample_size": ess,
        "effective_sample_ratio": ess / n if n > 0 else 0.0,
        "max_importance_weight": float(np.max(w)) if n > 0 else 0.0,
    }


def trust_level(decision_sources) -> str:
    """
    Classify the overall trust level of an OPE result from decision provenance.

    "audit-grade" only if every logged decision came from a source with a known,
    correct propensity (Bandit Brain's own /decide, i.e. "served"). Anything else
    — a client-supplied or estimated propensity — is downgraded to "best-effort":
    refusing to call a possibly-biased number audit-grade is the core anti-snake-oil
    feature (see ROADMAP's "Two ingestion modes, one schema").
    """
    sources = set(decision_sources)
    if sources and sources <= TRUSTED_SOURCES:
        return "audit-grade"
    return "best-effort"


def evaluate(
    rewards,
    logging_propensities,
    target_propensities,
    decision_sources=None,
    estimator: str = "snips",
    rng: np.random.Generator | None = None,
) -> dict:
    """
    Evaluate a target policy from logged data with one call: point estimate, a
    95% confidence interval, reliability diagnostics, and a provenance-aware
    trust label — the full result a promotion decision should be gated on.
    """
    if estimator not in ("ips", "snips"):
        raise ValueError(f"estimator must be 'ips' or 'snips', got {estimator!r}")

    if estimator == "ips":
        estimate = ips_estimate(rewards, logging_propensities, target_propensities)
        ci_lower, ci_upper = ips_confidence_interval(rewards, logging_propensities, target_propensities)
    else:
        estimate = snips_estimate(rewards, logging_propensities, target_propensities)
        ci_lower, ci_upper = snips_confidence_interval(rewards, logging_propensities, target_propensities, rng=rng)

    diagnostics = propensity_overlap(logging_propensities, target_propensities)
    return {
        "estimator": estimator,
        "estimate": estimate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "confidence": DEFAULT_CONFIDENCE,
        "trust_level": trust_level(decision_sources) if decision_sources is not None else "best-effort",
        **diagnostics,
    }
