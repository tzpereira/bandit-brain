from banditbrain.core.policies import EpsilonGreedyBandit
from banditbrain.simulation.sensitivity import sweep

TRUE_CTRS = [0.1, 0.5]


def test_sweep_returns_one_result_per_param_value():
    def builder(epsilon):
        def factory(metrics, rng):
            return EpsilonGreedyBandit(metrics, epsilon=epsilon).allocate()

        return factory

    results = sweep([0.05, 0.5], builder, TRUE_CTRS, horizon=200, n_seeds=5)

    assert [r["param_value"] for r in results] == [0.05, 0.5]
    assert all("final_mean_regret" in r and "mean_total_reward" in r for r in results)


def test_sweep_shows_higher_epsilon_costs_more_regret():
    # With a well-separated best arm, more forced random exploration (higher
    # epsilon) should mean strictly more cumulative regret over the same horizon.
    def builder(epsilon):
        def factory(metrics, rng):
            return EpsilonGreedyBandit(metrics, epsilon=epsilon).allocate()

        return factory

    results = sweep([0.01, 0.5], builder, TRUE_CTRS, horizon=300, n_seeds=10)
    low_eps, high_eps = results
    assert low_eps["final_mean_regret"] < high_eps["final_mean_regret"]
