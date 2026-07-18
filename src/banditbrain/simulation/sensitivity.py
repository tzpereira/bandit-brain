"""
Sensitivity sweeps: run the same environment against a policy across a range
of hyperparameter values (or bias-control settings) and report how the
headline numbers move — "the tuning story" the roadmap asks for, not just a
single cherry-picked configuration.
"""

from banditbrain.simulation.runner import run_many_seeds


def sweep(param_values: list, policy_factory_builder, true_ctrs: list[float], horizon: int, n_seeds: int) -> list[dict]:
    """
    For each value in `param_values`, build a policy factory via
    `policy_factory_builder(value) -> (metrics, rng) -> np.ndarray` and run it
    across `n_seeds` environments. Returns one summary dict per value.
    """
    results = []
    for value in param_values:
        factory = policy_factory_builder(value)
        result = run_many_seeds(factory, true_ctrs, horizon, n_seeds)
        results.append(
            {
                "param_value": value,
                "final_mean_regret": result["final_mean_regret"],
                "mean_total_reward": result["mean_total_reward"],
            }
        )
    return results
