"""
Multi-Armed Bandit Algorithms for Variant Allocation

Implements Epsilon-Greedy, UCB, Thompson Sampling, and Softmax algorithms for traffic allocation in online experiments.
"""

import numpy as np
import logging
from typing import List, Optional
from app.models import Metric, Allocation


###############################################################
# Epsilon-Greedy algorithm for variant allocation
###############################################################
class EpsilonGreedyBandit:
    """
    Epsilon-Greedy: Simple, intuitive, and fast. Use when you want a basic balance between exploration (random) and exploitation (best CTR).
    Tradeoff: High epsilon wastes traffic; low epsilon may miss better variants. Does not use uncertainty/confidence.
    """
    def __init__(self, metrics: List[Metric], epsilon: float = 0.1, experiment_name: str = "", date: Optional[str] = None):
        assert 0.0 <= epsilon <= 1.0, "epsilon must be in [0, 1]"
        self.metrics = metrics
        self.epsilon = epsilon
        self.variant_names = [m.variant_name for m in metrics]
        self.experiment_name = experiment_name
        self.date = date if date is not None else ""

    def select(self) -> str:
        if np.random.rand() < self.epsilon:
            # Exploration: choose a random variant
            return np.random.choice(self.variant_names)
        else:
            # Exploitation: choose the variant with the highest CTR
            ctrs = [m.ctr for m in self.metrics]
            max_ctr = max(ctrs)
            best = [m.variant_name for m in self.metrics if m.ctr == max_ctr]
            return np.random.choice(best)

    def get_allocation(self) -> List[Allocation]:
        best = self.select()
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=1.0 if name == best else 0.0,
                algorithm="eg",
                date=self.date
            )
            for name in self.variant_names
        ]


###############################################################
# UCB algorithm for variant allocation
###############################################################
class UCBBandit:
    """
    UCB: Uses confidence bounds to balance exploration and exploitation. Good for non-stationary or uncertain environments.
    Tradeoff: 'c' controls exploration. Can be sensitive to parameter choice. More robust than epsilon-greedy.
    """
    def __init__(self, metrics: List[Metric], c: float = 2.0, experiment_name: str = "", date: Optional[str] = None):
        assert c > 0, "c must be positive"
        self.metrics = metrics
        self.c = c
        self.variant_names = [m.variant_name for m in metrics]
        self.total_impressions = sum(m.impressions for m in metrics) + 1
        self.experiment_name = experiment_name
        self.date = date if date is not None else ""

    def select(self) -> str:
        scores = []
        for m in self.metrics:
            if m.impressions > 0:
                ucb = m.ctr + self.c * np.sqrt(np.log(self.total_impressions) / m.impressions)
            else:
                ucb = 1.0  # Explore variants with no history
            scores.append((m.variant_name, ucb))
        max_ucb = max(score for _, score in scores)
        best = [name for name, score in scores if score == max_ucb]
        return np.random.choice(best)

    def get_allocation(self) -> List[Allocation]:
        best = self.select()
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=1.0 if name == best else 0.0,
                algorithm="ucb",
                date=self.date
            )
            for name in self.variant_names
        ]


###############################################################
# Thompson Sampling algorithm for variant allocation
###############################################################
class ThompsonSamplingBandit:
    """
    Thompson Sampling: Bayesian approach, naturally balances exploration/exploitation. Excellent for sparse or uncertain data.
    Tradeoff: More computationally intensive. Requires probabilistic modeling.
    """
    def __init__(self, metrics: List[Metric], experiment_name: str = "", date: Optional[str] = None):
        self.metrics = metrics
        self.variant_names = [m.variant_name for m in metrics]
        self.experiment_name = experiment_name
        self.date = date if date is not None else ""

    def select(self) -> str:
        samples = []
        for m in self.metrics:
            # Beta posterior: alpha = 1 + clicks, beta = 1 + impressions - clicks
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

    def get_allocation(self) -> List[Allocation]:
        best = self.select()
        return [
            Allocation(
                experiment_name=self.experiment_name,
                variant_name=name,
                allocated_pct=1.0 if name == best else 0.0,
                algorithm="ts",
                date=self.date
            )
            for name in self.variant_names
        ]


# ###############################################################
# Softmax Bandit algorithm for proportional allocation
# ###############################################################
class SoftmaxBandit:
    """
    Softmax: Allocates traffic proportionally to scores (CTR). Use when you want all variants to receive some traffic, but favor better ones.
    Tradeoff: Tau controls exploration. Higher tau = more uniform, lower tau = more greedy.
    """
    def __init__(self, metrics: List[Metric], tau: float = 0.1, experiment_name: str = "", date: Optional[str] = None):
        assert tau > 0, "tau must be positive"
        self.metrics = metrics
        self.tau = tau
        self.variant_names = [m.variant_name for m in metrics]
        self.experiment_name = experiment_name
        self.date = date if date is not None else ""

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

    def get_allocation(self) -> List[Allocation]:
        ctrs = np.array([m.ctr for m in self.metrics])
        probs = self._softmax(ctrs, tau=self.tau)
        allocations = []
        for name, pct in zip(self.variant_names, probs):
            allocations.append(
                Allocation(
                    experiment_name=self.experiment_name,
                    variant_name=name,
                    allocated_pct=float(pct),
                    algorithm="softmax",
                    date=self.date
                )
            )
        return allocations