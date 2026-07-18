"""
Run a policy (or baseline) against a BernoulliBanditEnv, one round at a time:
see cumulative per-arm counts so far -> allocate -> sample an arm -> observe a
reward -> update counts -> repeat. This is the same shape as the serve loop
(core.policies.BanditPolicy.get_allocation() + core.decide.sample_decision),
so the simulation is exercising the real production code path, not a
simulation-only reimplementation of the algorithms.
"""

import numpy as np

from banditbrain.core.models import Metric
from banditbrain.simulation.environment import BernoulliBanditEnv


def _metrics_from_counts(variant_names: list[str], impressions: list[int], clicks: list[int]) -> list[Metric]:
    metrics = []
    for name, imp, clk in zip(variant_names, impressions, clicks, strict=True):
        ctr = clk / imp if imp > 0 else 0.0
        metrics.append(
            Metric(
                variant_name=name,
                clicks=clk,
                impressions=imp,
                total_cost=0.0,
                device="all",
                location="all",
                user_segment="all",
                ctr=ctr,
                ctr_se=0.0,
                ctr_ci_lower=0.0,
                ctr_ci_upper=1.0,
            )
        )
    return metrics


def run_policy(policy_factory, env: BernoulliBanditEnv, horizon: int, seed: int) -> dict:
    """
    Run one policy for `horizon` rounds against one environment instance.

    Args:
        policy_factory: ``(metrics: list[Metric], rng: np.random.Generator) -> np.ndarray``,
            a probability vector over the arms. Deterministic policies/baselines
            ignore `rng`; Thompson Sampling uses it to seed its internal draws.
        env: the environment to pull from (its own seed controls reward draws).
        horizon: number of rounds to run.
        seed: seeds arm *selection* and any policy-internal randomness — independent
            of env's own seed, so the same policy run is reproducible regardless of
            how the environment's reward draws are seeded.

    Returns per-round arrays plus the cumulative regret curve.
    """
    variant_names = [f"arm_{i}" for i in range(env.n_arms)]
    impressions = [0] * env.n_arms
    clicks = [0] * env.n_arms
    rng = np.random.default_rng(seed)

    chosen_arms = np.empty(horizon, dtype=int)
    rewards = np.empty(horizon, dtype=int)
    propensities = np.empty(horizon, dtype=float)
    regret = np.empty(horizon, dtype=float)

    for t in range(horizon):
        metrics = _metrics_from_counts(variant_names, impressions, clicks)
        probs = policy_factory(metrics, rng)
        arm = int(rng.choice(env.n_arms, p=probs))
        reward = env.pull(arm)

        chosen_arms[t] = arm
        rewards[t] = reward
        propensities[t] = probs[arm]
        regret[t] = env.best_ctr - env.true_ctrs[arm]

        impressions[arm] += 1
        clicks[arm] += reward

    return {
        "chosen_arms": chosen_arms,
        "rewards": rewards,
        "propensities": propensities,
        "regret": regret,
        "cumulative_regret": np.cumsum(regret),
    }


def run_many_seeds(policy_factory, true_ctrs: list[float], horizon: int, n_seeds: int, base_seed: int = 0) -> dict:
    """
    Run `run_policy` across `n_seeds` independent environment instances and
    aggregate: mean cumulative-regret curve with a 95% CI band, final regret,
    and mean total reward (the input to the "extra clicks vs A/B" headline metric).
    """
    best_arm = int(np.argmax(true_ctrs))
    all_cumulative_regret = np.empty((n_seeds, horizon))
    total_rewards = np.empty(n_seeds)
    pct_best_arm = np.empty(n_seeds)

    for s in range(n_seeds):
        env = BernoulliBanditEnv(true_ctrs, seed=base_seed + s)
        result = run_policy(policy_factory, env, horizon, seed=base_seed + s + 1_000_000)
        all_cumulative_regret[s] = result["cumulative_regret"]
        total_rewards[s] = result["rewards"].sum()
        pct_best_arm[s] = float(np.mean(result["chosen_arms"] == best_arm))

    mean_curve = all_cumulative_regret.mean(axis=0)
    if n_seeds > 1:
        se_curve = all_cumulative_regret.std(axis=0, ddof=1) / np.sqrt(n_seeds)
    else:
        se_curve = np.zeros_like(mean_curve)

    return {
        "mean_cumulative_regret": mean_curve,
        "ci_lower": mean_curve - 1.96 * se_curve,
        "ci_upper": mean_curve + 1.96 * se_curve,
        "final_mean_regret": float(mean_curve[-1]),
        "final_regret_ci_lower": float(mean_curve[-1] - 1.96 * se_curve[-1]),
        "final_regret_ci_upper": float(mean_curve[-1] + 1.96 * se_curve[-1]),
        "mean_total_reward": float(total_rewards.mean()),
        "total_reward_per_seed": total_rewards,
        "pct_traffic_on_best_arm": float(pct_best_arm.mean()),
    }


def extra_reward_vs_baseline(policy_result: dict, baseline_result: dict) -> float:
    """The headline number: mean total reward under the policy minus under the baseline."""
    return policy_result["mean_total_reward"] - baseline_result["mean_total_reward"]
