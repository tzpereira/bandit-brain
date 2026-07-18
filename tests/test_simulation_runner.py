import numpy as np
import pytest

from banditbrain.core.policies import EpsilonGreedyBandit, ThompsonSamplingBandit
from banditbrain.simulation.baselines import oracle_allocation, uniform_allocation
from banditbrain.simulation.environment import BernoulliBanditEnv
from banditbrain.simulation.runner import extra_reward_vs_baseline, run_many_seeds, run_policy

TRUE_CTRS = [0.1, 0.3, 0.2]


def uniform_factory(metrics, rng):
    return uniform_allocation(len(metrics))


def oracle_factory(best_arm):
    def factory(metrics, rng):
        return oracle_allocation(len(metrics), best_arm)

    return factory


def eg_factory(metrics, rng):
    return EpsilonGreedyBandit(metrics, epsilon=0.1).allocate()


def ts_factory(metrics, rng):
    # Fewer Monte Carlo draws than the production default (10k) — plenty for a
    # directional regret comparison in tests, much cheaper to run repeatedly.
    return ThompsonSamplingBandit(metrics, n_samples=500, seed=int(rng.integers(0, 2**32))).allocate()


def test_run_policy_produces_horizon_length_arrays():
    env = BernoulliBanditEnv(TRUE_CTRS, seed=0)
    result = run_policy(uniform_factory, env, horizon=500, seed=0)
    assert len(result["chosen_arms"]) == 500
    assert len(result["rewards"]) == 500
    assert result["cumulative_regret"][-1] == pytest.approx(result["regret"].sum())


def test_run_policy_is_reproducible_given_a_seed():
    env_a = BernoulliBanditEnv(TRUE_CTRS, seed=1)
    env_b = BernoulliBanditEnv(TRUE_CTRS, seed=1)
    result_a = run_policy(ts_factory, env_a, horizon=200, seed=7)
    result_b = run_policy(ts_factory, env_b, horizon=200, seed=7)
    np.testing.assert_array_equal(result_a["chosen_arms"], result_b["chosen_arms"])
    np.testing.assert_array_equal(result_a["rewards"], result_b["rewards"])


def test_oracle_has_zero_regret():
    env = BernoulliBanditEnv(TRUE_CTRS, seed=0)
    result = run_policy(oracle_factory(env.best_arm), env, horizon=1000, seed=0)
    assert result["cumulative_regret"][-1] == pytest.approx(0.0)


def test_real_policies_beat_uniform_and_lose_to_oracle():
    n_seeds = 10
    horizon = 300
    uniform_result = run_many_seeds(uniform_factory, TRUE_CTRS, horizon, n_seeds)
    oracle_result = run_many_seeds(oracle_factory(int(np.argmax(TRUE_CTRS))), TRUE_CTRS, horizon, n_seeds)
    eg_result = run_many_seeds(eg_factory, TRUE_CTRS, horizon, n_seeds)
    ts_result = run_many_seeds(ts_factory, TRUE_CTRS, horizon, n_seeds)

    # Oracle: zero regret, ceiling for reward.
    assert oracle_result["final_mean_regret"] == pytest.approx(0.0)
    # Real policies must incur less cumulative regret than a fixed uniform split...
    assert eg_result["final_mean_regret"] < uniform_result["final_mean_regret"]
    assert ts_result["final_mean_regret"] < uniform_result["final_mean_regret"]
    # ...and strictly more than the oracle ceiling (can't beat known ground truth).
    assert eg_result["final_mean_regret"] > oracle_result["final_mean_regret"]
    assert ts_result["final_mean_regret"] > oracle_result["final_mean_regret"]


def test_extra_reward_vs_baseline_is_positive_for_a_real_policy():
    n_seeds = 10
    horizon = 300
    uniform_result = run_many_seeds(uniform_factory, TRUE_CTRS, horizon, n_seeds)
    ts_result = run_many_seeds(ts_factory, TRUE_CTRS, horizon, n_seeds)
    extra = extra_reward_vs_baseline(ts_result, uniform_result)
    assert extra > 0


def test_pct_traffic_on_best_arm_is_higher_for_real_policies_than_uniform():
    n_seeds = 10
    horizon = 300
    uniform_result = run_many_seeds(uniform_factory, TRUE_CTRS, horizon, n_seeds)
    oracle_result = run_many_seeds(oracle_factory(int(np.argmax(TRUE_CTRS))), TRUE_CTRS, horizon, n_seeds)
    ts_result = run_many_seeds(ts_factory, TRUE_CTRS, horizon, n_seeds)

    assert oracle_result["pct_traffic_on_best_arm"] == pytest.approx(1.0)
    assert uniform_result["pct_traffic_on_best_arm"] == pytest.approx(1.0 / 3, abs=0.05)
    assert ts_result["pct_traffic_on_best_arm"] > uniform_result["pct_traffic_on_best_arm"]
