"""
Multi-Armed Bandit Algorithms for Variant Allocation

Implements Epsilon-Greedy, UCB, Thompson Sampling, and Softmax algorithms for
traffic allocation in online experiments.

Every policy returns a *fractional distribution* over the variants (probabilities
that sum to 1), not an all-or-nothing pick of a single winner. This is the correct
shape for daily batch allocation: it splits the day's traffic across variants and
keeps exploring. The allocations are also reproducible — deterministic given the
input metrics, and for the sampling-based policy (Thompson) deterministic given the
metrics *and* a seed.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np

from banditbrain.core.dates import get_prediction_date
from banditbrain.core.models import Allocation, Metric

# Number of Monte Carlo draws used to estimate P(arm is best) for Thompson Sampling.
DEFAULT_TS_SAMPLES = 10_000


class BanditPolicy(ABC):
    """
    Shared interface for every allocation policy.

    Subclasses implement :meth:`allocate`, which returns a probability vector over
    ``self.variant_names`` (same order, summing to 1). :meth:`get_allocation` wraps
    that vector into the ``Allocation`` records the API and dashboard consume.
    """

    algorithm: ClassVar[str]

    def __init__(
        self,
        metrics: list[Metric],
        *,
        experiment_name: str = "",
        date: str | None = None,
        seed: int | None = None,
    ):
        self.metrics = metrics
        self.variant_names = [m.variant_name for m in metrics]
        self.experiment_name = experiment_name
        self.date = date
        # A per-instance generator keeps sampling reproducible and isolated from the
        # global numpy RNG state. Same metrics + same seed -> identical allocation.
        self.rng = np.random.default_rng(seed)

    @abstractmethod
    def allocate(self) -> np.ndarray:
        """Return the traffic distribution over ``self.variant_names`` (sums to 1)."""
        raise NotImplementedError

    def get_allocation(self) -> list[Allocation]:
        probs = self.allocate()
        prediction_date_str = get_prediction_date(self.date)
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=float(pct),
                algorithm=self.algorithm,
                date=prediction_date_str,
            )
            for name, pct in zip(self.variant_names, probs, strict=True)
        ]


###############################################################
# Epsilon-Greedy algorithm for variant allocation
###############################################################
class EpsilonGreedyBandit(BanditPolicy):
    """
    Epsilon-Greedy: Simple, intuitive, and fast. Use when you want a basic balance
    between exploration (random) and exploitation (best CTR).
    Tradeoff: High epsilon wastes traffic; low epsilon may miss better variants.
    Does not use uncertainty/confidence.

    Batch form: give ``(1 - epsilon)`` to the empirical best arm and spread
    ``epsilon`` uniformly (``epsilon / K`` each) across all arms. Deterministic
    given the metrics. Ties for the best arm split the exploitation mass equally.
    """

    algorithm = "eg"

    def __init__(
        self,
        metrics: list[Metric],
        epsilon: float = 0.1,
        *,
        experiment_name: str = "",
        date: str | None = None,
        seed: int | None = None,
    ):
        assert 0.0 <= epsilon <= 1.0, "epsilon must be in [0, 1]"
        super().__init__(metrics, experiment_name=experiment_name, date=date, seed=seed)
        self.epsilon = epsilon

    def allocate(self) -> np.ndarray:
        ctrs = np.array([m.ctr for m in self.metrics], dtype=float)
        n = len(ctrs)
        probs = np.full(n, self.epsilon / n)
        best_mask = ctrs == ctrs.max()
        probs[best_mask] += (1.0 - self.epsilon) / int(best_mask.sum())
        return probs


###############################################################
# UCB algorithm for variant allocation
###############################################################
class UCBBandit(BanditPolicy):
    """
    UCB: Uses confidence bounds to balance exploration and exploitation.
    Good for non-stationary or uncertain environments.
    Tradeoff: 'c' controls exploration. Can be sensitive to parameter choice.
    More robust than epsilon-greedy.

    Batch form: UCB is a ranking rule, not a distribution, so we adapt it the same
    way as epsilon-greedy — give ``(1 - exploration_floor)`` to the arm with the
    highest UCB score and spread ``exploration_floor`` uniformly across all arms.
    Never-shown arms get an infinite (maximally optimistic) score so they are tried
    first. Deterministic given the metrics; ties share the top-arm mass equally.
    """

    algorithm = "ucb"

    def __init__(
        self,
        metrics: list[Metric],
        c: float = 2.0,
        *,
        exploration_floor: float = 0.1,
        experiment_name: str = "",
        date: str | None = None,
        seed: int | None = None,
    ):
        assert c > 0, "c must be positive"
        assert 0.0 <= exploration_floor <= 1.0, "exploration_floor must be in [0, 1]"
        super().__init__(metrics, experiment_name=experiment_name, date=date, seed=seed)
        self.c = c
        self.exploration_floor = exploration_floor
        self.total_impressions = sum(m.impressions for m in metrics) + 1

    def allocate(self) -> np.ndarray:
        scores = np.array(
            [
                m.ctr + self.c * np.sqrt(np.log(self.total_impressions) / m.impressions)
                if m.impressions > 0
                else np.inf  # unexplored arm: maximally optimistic, explore it first
                for m in self.metrics
            ],
            dtype=float,
        )
        n = len(scores)
        probs = np.full(n, self.exploration_floor / n)
        best_mask = scores == scores.max()
        probs[best_mask] += (1.0 - self.exploration_floor) / int(best_mask.sum())
        return probs


###############################################################
# Thompson Sampling algorithm for variant allocation
###############################################################
class ThompsonSamplingBandit(BanditPolicy):
    """
    Thompson Sampling: Bayesian approach, naturally balances exploration/exploitation.
    Excellent for sparse or uncertain data.
    Tradeoff: More computationally intensive. Requires probabilistic modeling.

    Batch form: allocate to each arm in proportion to ``P(arm is the best)``,
    estimated by Monte Carlo over the per-arm Beta posteriors — draw many samples
    from every posterior and count how often each arm wins. A single Beta draw
    (the old behaviour) collapses to one winner and throws away this probability;
    the Monte Carlo estimate is the correct fractional allocation. Reproducible
    given the metrics and a seed.
    """

    algorithm = "ts"

    def __init__(
        self,
        metrics: list[Metric],
        *,
        n_samples: int = DEFAULT_TS_SAMPLES,
        experiment_name: str = "",
        date: str | None = None,
        seed: int | None = None,
    ):
        assert n_samples > 0, "n_samples must be positive"
        super().__init__(metrics, experiment_name=experiment_name, date=date, seed=seed)
        self.n_samples = n_samples

    def allocate(self) -> np.ndarray:
        n = len(self.metrics)
        samples = np.empty((n, self.n_samples))
        for i, m in enumerate(self.metrics):
            # Beta(1, 1) prior; a never-shown arm stays uniform on [0, 1].
            alpha = 1.0 + m.clicks
            beta = 1.0 + (m.impressions - m.clicks)
            # Defensive clamp: the schema enforces clicks <= impressions, so alpha
            # and beta are already >= 1, but guard against degenerate inputs.
            alpha = max(alpha, 1e-9)
            beta = max(beta, 1e-9)
            samples[i] = self.rng.beta(alpha, beta, size=self.n_samples)
        winners = np.argmax(samples, axis=0)
        counts = np.bincount(winners, minlength=n)
        return counts / self.n_samples


###############################################################
# Softmax Bandit algorithm for proportional allocation
###############################################################
class SoftmaxBandit(BanditPolicy):
    """
    Softmax: Allocates traffic proportionally to scores (CTR). Use when you want all
    variants to receive some traffic, but favor better ones.
    Tradeoff: Tau controls exploration. Higher tau = more uniform, lower tau = more
    greedy. Already a proper fractional distribution and deterministic given the data.
    """

    algorithm = "softmax"

    def __init__(
        self,
        metrics: list[Metric],
        tau: float = 0.1,
        *,
        experiment_name: str = "",
        date: str | None = None,
        seed: int | None = None,
    ):
        assert tau > 0, "tau must be positive"
        super().__init__(metrics, experiment_name=experiment_name, date=date, seed=seed)
        self.tau = tau

    @staticmethod
    def _softmax(x: np.ndarray, tau: float = 0.1) -> np.ndarray:
        """
        Numerically stable softmax function.
        Args:
            x: Array of scores.
            tau: Temperature parameter.
        Returns:
            Array of probabilities summing to 1.
        """
        x = np.array(x, dtype=float)
        x_adj = x - np.max(x)
        exp_x = np.exp(x_adj / tau)
        return exp_x / np.sum(exp_x)

    def allocate(self) -> np.ndarray:
        ctrs = np.array([m.ctr for m in self.metrics], dtype=float)
        return self._softmax(ctrs, tau=self.tau)
