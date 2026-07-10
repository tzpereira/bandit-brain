"""
Multi-Armed Bandit Algorithms for Variant Allocation

Implements Epsilon-Greedy, UCB, Thompson Sampling, and Softmax algorithms for traffic allocation in online experiments.
"""

import logging

import numpy as np

from banditbrain.core.dates import get_prediction_date
from banditbrain.core.models import Allocation, Metric


###############################################################
# Epsilon-Greedy algorithm for variant allocation
###############################################################
class EpsilonGreedyBandit:
    """
    Epsilon-Greedy: Simple, intuitive, and fast. Use when you want a basic balance
    between exploration (random) and exploitation (best CTR).
    Tradeoff: High epsilon wastes traffic; low epsilon may miss better variants.
    Does not use uncertainty/confidence.
    """

    def __init__(self, metrics: list[Metric], epsilon: float = 0.1, experiment_name: str = "", date: str | None = None):
        assert 0.0 <= epsilon <= 1.0, "epsilon must be in [0, 1]"
        self.metrics = metrics
        self.epsilon = epsilon
        self.variant_names = [m.variant_name for m in metrics]
        self.experiment_name = experiment_name
        self.date = date

    def select(self) -> str:
        if np.random.rand() < self.epsilon:
            return np.random.choice(self.variant_names)  # Exploration
        else:
            ctrs = [m.ctr for m in self.metrics]
            max_ctr = max(ctrs)
            best = [m.variant_name for m in self.metrics if m.ctr == max_ctr]
            return np.random.choice(best)  # Exploitation

    def get_allocation(self) -> list[Allocation]:
        best = self.select()
        prediction_date_str = get_prediction_date(self.date)
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=1.0 if name == best else 0.0,
                algorithm="eg",
                date=prediction_date_str,
            )
            for name in self.variant_names
        ]


###############################################################
# UCB algorithm for variant allocation
###############################################################
class UCBBandit:
    """
    UCB: Uses confidence bounds to balance exploration and exploitation.
    Good for non-stationary or uncertain environments.
    Tradeoff: 'c' controls exploration. Can be sensitive to parameter choice.
    More robust than epsilon-greedy.
    """

    def __init__(self, metrics: list[Metric], c: float = 2.0, experiment_name: str = "", date: str | None = None):
        assert c > 0, "c must be positive"
        self.metrics = metrics
        self.c = c
        self.variant_names = [m.variant_name for m in metrics]
        self.total_impressions = sum(m.impressions for m in metrics) + 1
        self.experiment_name = experiment_name
        self.date = date

    def select(self) -> str:
        scores = []
        for m in self.metrics:
            # Variants with no history get the maximum optimistic score.
            ucb = m.ctr + self.c * np.sqrt(np.log(self.total_impressions) / m.impressions) if m.impressions > 0 else 1.0
            scores.append((m.variant_name, ucb))
        max_ucb = max(score for _, score in scores)
        best = [name for name, score in scores if score == max_ucb]
        return np.random.choice(best)

    def get_allocation(self) -> list[Allocation]:
        best = self.select()
        prediction_date_str = get_prediction_date(self.date)
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=1.0 if name == best else 0.0,
                algorithm="ucb",
                date=prediction_date_str,
            )
            for name in self.variant_names
        ]


###############################################################
# Thompson Sampling algorithm for variant allocation
###############################################################
class ThompsonSamplingBandit:
    """
    Thompson Sampling: Bayesian approach, naturally balances exploration/exploitation.
    Excellent for sparse or uncertain data.
    Tradeoff: More computationally intensive. Requires probabilistic modeling.
    """

    def __init__(self, metrics: list[Metric], experiment_name: str = "", date: str | None = None):
        self.metrics = metrics
        self.variant_names = [m.variant_name for m in metrics]
        self.experiment_name = experiment_name
        self.date = date

    def select(self) -> str:
        samples = []
        for m in self.metrics:
            alpha = 1 + m.clicks
            beta = 1 + m.impressions - m.clicks
            if alpha <= 0 or beta <= 0:
                logging.warning(f"Non-positive alpha/beta for variant {m.variant_name}: alpha={alpha}, beta={beta}")
                sample = 0.0
            else:
                sample = np.random.beta(alpha, beta)
            samples.append((m.variant_name, sample))
        max_sample = max(sample for _, sample in samples)
        best = [name for name, sample in samples if sample == max_sample]
        return np.random.choice(best)

    def get_allocation(self) -> list[Allocation]:
        best = self.select()
        prediction_date_str = get_prediction_date(self.date)
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=1.0 if name == best else 0.0,
                algorithm="ts",
                date=prediction_date_str,
            )
            for name in self.variant_names
        ]


###############################################################
# Softmax Bandit algorithm for proportional allocation
###############################################################
class SoftmaxBandit:
    """
    Softmax: Allocates traffic proportionally to scores (CTR). Use when you want all
    variants to receive some traffic, but favor better ones.
    Tradeoff: Tau controls exploration. Higher tau = more uniform, lower tau = more greedy.
    """

    def __init__(self, metrics: list[Metric], tau: float = 0.1, experiment_name: str = "", date: str | None = None):
        assert tau > 0, "tau must be positive"
        self.metrics = metrics
        self.tau = tau
        self.variant_names = [m.variant_name for m in metrics]
        self.experiment_name = experiment_name
        self.date = date

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
        x = np.array(x)
        x_adj = x - np.max(x)
        exp_x = np.exp(x_adj / tau)
        return exp_x / np.sum(exp_x)

    def get_allocation(self) -> list[Allocation]:
        ctrs = np.array([m.ctr for m in self.metrics])
        probs = self._softmax(ctrs, tau=self.tau)
        prediction_date_str = get_prediction_date(self.date)
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=float(pct),
                algorithm="softmax",
                date=prediction_date_str,
            )
            for name, pct in zip(self.variant_names, probs, strict=True)
        ]
