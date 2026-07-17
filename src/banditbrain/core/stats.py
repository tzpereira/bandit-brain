"""
Statistical helpers for CTR estimation.

Uses the Wilson score interval rather than the normal approximation for
confidence bounds: the normal approximation collapses to a degenerate [0, 0]
interval whenever clicks == 0 (understating uncertainty for exactly the
sparse-data arms a bandit most needs to reason honestly about), and is
undefined at impressions == 0. Wilson stays well-behaved through both.
"""

import math

# Z-score for a two-sided 95% confidence interval.
DEFAULT_Z = 1.96


def wilson_score_interval(clicks: int, impressions: int, z: float = DEFAULT_Z) -> tuple[float, float]:
    """
    Wilson score confidence interval for a click-through rate.

    An arm with zero impressions carries no information about its true CTR, so
    it returns the maximally uninformative interval (0.0, 1.0) rather than the
    (0.0, 0.0) a naive formula would silently produce.
    """
    if impressions <= 0:
        return 0.0, 1.0

    p = clicks / impressions
    n = impressions
    z2 = z * z
    denominator = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denominator
    margin = (z * math.sqrt((p * (1 - p) / n) + (z2 / (4 * n * n)))) / denominator
    return max(center - margin, 0.0), min(center + margin, 1.0)


def standard_error(clicks: int, impressions: int) -> float:
    """Normal-approximation standard error of the CTR estimate; 0.0 when unobserved."""
    if impressions <= 0:
        return 0.0
    p = clicks / impressions
    return math.sqrt(p * (1 - p) / impressions)
