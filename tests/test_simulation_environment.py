import numpy as np
import pytest

from banditbrain.simulation.environment import BernoulliBanditEnv


def test_best_arm_and_best_ctr_reflect_true_ctrs():
    env = BernoulliBanditEnv([0.1, 0.3, 0.2])
    assert env.best_arm == 1
    assert env.best_ctr == pytest.approx(0.3)


def test_pull_returns_binary_rewards():
    env = BernoulliBanditEnv([0.5, 0.5], seed=0)
    rewards = [env.pull(0) for _ in range(100)]
    assert set(rewards) <= {0, 1}


def test_pull_matches_the_true_ctr_at_large_sample_size():
    env = BernoulliBanditEnv([0.2, 0.8], seed=0)
    draws = np.array([env.pull(0) for _ in range(50_000)])
    assert draws.mean() == pytest.approx(0.2, abs=0.01)


def test_pull_is_reproducible_given_a_seed():
    rewards_a = [BernoulliBanditEnv([0.3, 0.6], seed=42).pull(0) for _ in range(20)]
    rewards_b = [BernoulliBanditEnv([0.3, 0.6], seed=42).pull(0) for _ in range(20)]
    # Each call re-seeds a fresh env, so the two runs should match exactly.
    assert rewards_a == rewards_b


def test_rejects_invalid_ctrs():
    with pytest.raises(AssertionError):
        BernoulliBanditEnv([0.5, 1.5])


def test_requires_at_least_two_arms():
    with pytest.raises(AssertionError):
        BernoulliBanditEnv([0.5])
