"""
Phase 2 headline report: prove the bandit policies beat a fixed A/B split, and
that the OPE estimators recover known ground truth with correct CI coverage.

Everything printed here is measured, not asserted — this script is the
reproducible source of the numbers ROADMAP.md Phase 2 claims. See
banditbrain.simulation.demo for the shared scenario/policy configuration also
used by scripts/generate_figures.py.

Usage:
    uv run python scripts/simulation_report.py
"""

from banditbrain.core.policies import EpsilonGreedyBandit
from banditbrain.simulation.baselines import fixed_split_allocation, uniform_allocation
from banditbrain.simulation.demo import (
    BASELINE_NAME,
    HORIZON,
    N_SEEDS,
    REAL_POLICY_NAMES,
    TRUE_CTRS,
    run_all_policies,
)
from banditbrain.simulation.runner import extra_reward_vs_baseline
from banditbrain.simulation.sensitivity import sweep
from banditbrain.simulation.validate_ope import check_ope_coverage


def print_regret_section() -> dict:
    print("=" * 78)
    print(f"REGRET vs BASELINES  (true CTRs A/B/C = {TRUE_CTRS}, horizon={HORIZON}, n_seeds={N_SEEDS})")
    print("=" * 78)

    results = run_all_policies()
    for name, r in results.items():
        print(
            f"{name:<20s} final_mean_regret={r['final_mean_regret']:8.2f} "
            f"(95% CI [{r['final_regret_ci_lower']:6.2f}, {r['final_regret_ci_upper']:6.2f}])   "
            f"mean_total_reward={r['mean_total_reward']:8.2f}   "
            f"%best_arm={r['pct_traffic_on_best_arm']:5.1%}"
        )

    print()
    baseline = results[BASELINE_NAME]
    print(f"HEADLINE NUMBER — extra reward (clicks) vs {BASELINE_NAME} over the same horizon/seeds:")
    for name in REAL_POLICY_NAMES:
        extra = extra_reward_vs_baseline(results[name], baseline)
        print(f"  {name:<20s} +{extra:7.2f} extra clicks vs uniform, over {HORIZON} decisions")
    print()
    return results


def print_ope_validation_section() -> None:
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


def print_sensitivity_section() -> None:
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
