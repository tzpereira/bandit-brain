"""
Phase 2 headline report: prove the bandit policies beat a fixed A/B split, and
that the OPE estimators recover known ground truth with correct CI coverage.

Everything printed here is measured, not asserted — this script is the
reproducible source of the numbers ROADMAP.md Phase 2 claims. Uses the same
true CTRs as the seeded example_ads dataset (scripts/generate_example_data.py)
so the simulation's story matches the demo's.

Usage:
    uv run python scripts/simulation_report.py
"""

import numpy as np

from banditbrain.core.policies import EpsilonGreedyBandit, SoftmaxBandit, ThompsonSamplingBandit, UCBBandit
from banditbrain.simulation.baselines import fixed_split_allocation, oracle_allocation, uniform_allocation
from banditbrain.simulation.runner import extra_reward_vs_baseline, run_many_seeds
from banditbrain.simulation.sensitivity import sweep
from banditbrain.simulation.validate_ope import check_ope_coverage

TRUE_CTRS = [0.030, 0.055, 0.038]  # A, B, C — matches scripts/generate_example_data.py
HORIZON = 3_000
N_SEEDS = 50
TS_N_SAMPLES = 1_000  # fewer than production's 10k default; plenty for a regret comparison


def uniform_factory(metrics, rng):
    return uniform_allocation(len(metrics))


def oracle_factory(best_arm):
    def factory(metrics, rng):
        return oracle_allocation(len(metrics), best_arm)

    return factory


def fixed_90_10_factory(metrics, rng):
    return fixed_split_allocation(len(metrics), favored_arm=0, favored_share=0.9)


def eg_factory(metrics, rng):
    return EpsilonGreedyBandit(metrics, epsilon=0.1).allocate()


def ucb_factory(metrics, rng):
    return UCBBandit(metrics, c=2.0).allocate()


def ts_factory(metrics, rng):
    return ThompsonSamplingBandit(metrics, n_samples=TS_N_SAMPLES, seed=int(rng.integers(0, 2**32))).allocate()


def softmax_factory(metrics, rng):
    return SoftmaxBandit(metrics, tau=0.02).allocate()


def print_regret_section():
    print("=" * 78)
    print(f"REGRET vs BASELINES  (true CTRs A/B/C = {TRUE_CTRS}, horizon={HORIZON}, n_seeds={N_SEEDS})")
    print("=" * 78)

    best_arm = int(np.argmax(TRUE_CTRS))
    policies = {
        "uniform A/B/C": uniform_factory,
        "fixed 90/10": fixed_90_10_factory,
        "epsilon-greedy": eg_factory,
        "ucb": ucb_factory,
        "thompson sampling": ts_factory,
        "softmax": softmax_factory,
        "oracle (ceiling)": oracle_factory(best_arm),
    }

    results = {}
    for name, factory in policies.items():
        results[name] = run_many_seeds(factory, TRUE_CTRS, HORIZON, N_SEEDS)
        r = results[name]
        print(
            f"{name:<20s} final_mean_regret={r['final_mean_regret']:8.2f} "
            f"(95% CI [{r['final_regret_ci_lower']:6.2f}, {r['final_regret_ci_upper']:6.2f}])   "
            f"mean_total_reward={r['mean_total_reward']:8.2f}   "
            f"%best_arm={r['pct_traffic_on_best_arm']:5.1%}"
        )

    print()
    baseline = results["uniform A/B/C"]
    print("HEADLINE NUMBER — extra reward (clicks) vs uniform A/B/C over the same horizon/seeds:")
    for name in ("epsilon-greedy", "ucb", "thompson sampling", "softmax"):
        extra = extra_reward_vs_baseline(results[name], baseline)
        print(f"  {name:<20s} +{extra:7.2f} extra clicks vs uniform, over {HORIZON} decisions")
    print()
    return results


def print_ope_validation_section():
    print("=" * 78)
    print("OPE VALIDATION — does IPS/SNIPS recover known ground truth with correct coverage?")
    print("=" * 78)
    # Logging policy: uniform (full support/overlap). Target: the fixed 90/10 baseline.
    logging_probs = uniform_allocation(len(TRUE_CTRS)).tolist()
    target_probs = fixed_split_allocation(len(TRUE_CTRS), favored_arm=0, favored_share=0.9).tolist()

    for estimator in ("ips", "snips"):
        result = check_ope_coverage(
            true_ctrs=TRUE_CTRS,
            logging_probs=logging_probs,
            target_probs=target_probs,
            n_logged=2_000,
            n_trials=200,
            estimator=estimator,
            seed=0,
        )
        print(
            f"{estimator:<6s} true_value={result['true_value']:.4f}  "
            f"mean_bias={result['mean_bias']:+.5f}  "
            f"coverage_rate={result['coverage_rate']:.3f} (target: 0.95)  "
            f"[{result['n_trials']} trials x {result['n_logged']} logged decisions]"
        )
    print()


def print_sensitivity_section():
    print("=" * 78)
    print("SENSITIVITY SWEEP — epsilon-greedy's epsilon")
    print("=" * 78)

    def eg_builder(epsilon):
        def factory(metrics, rng):
            return EpsilonGreedyBandit(metrics, epsilon=epsilon).allocate()

        return factory

    for r in sweep([0.01, 0.05, 0.1, 0.3, 0.5], eg_builder, TRUE_CTRS, HORIZON, N_SEEDS):
        print(f"  epsilon={r['param_value']:<5} final_mean_regret={r['final_mean_regret']:8.2f}")
    print()


if __name__ == "__main__":
    print_regret_section()
    print_ope_validation_section()
    print_sensitivity_section()
