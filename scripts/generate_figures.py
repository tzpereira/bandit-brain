"""
Regenerate every headline figure for the README's Results section from a
clean clone. Uses the same scenario/policy configuration as
scripts/simulation_report.py (banditbrain.simulation.demo) — the printed
numbers and the plots always agree.

Usage:
    uv run python scripts/generate_figures.py

Writes PNGs to public/figures/.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

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
from banditbrain.simulation.validate_ope import run_ope_trials

OUT_DIR = Path(__file__).resolve().parent.parent / "public" / "figures"
DPI = 150


def plot_regret_curves(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(HORIZON)
    for name, r in results.items():
        line = ax.plot(x, r["mean_cumulative_regret"], label=name)[0]
        ax.fill_between(x, r["ci_lower"], r["ci_upper"], color=line.get_color(), alpha=0.15)
    ax.set_xlabel("Decision")
    ax.set_ylabel("Mean cumulative regret")
    ax.set_title(f"Cumulative regret vs. decisions (n_seeds={N_SEEDS}, shaded = 95% CI)")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "regret_curves.png", dpi=DPI)
    plt.close(fig)


def plot_algorithm_comparison(results: dict) -> None:
    baseline = results[BASELINE_NAME]
    names = REAL_POLICY_NAMES
    extras = [extra_reward_vs_baseline(results[name], baseline) for name in names]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["#4C72B0" if v >= 0 else "#C44E52" for v in extras]
    ax.bar(names, extras, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel(f"Extra clicks vs. {BASELINE_NAME}")
    ax.set_title(f"Algorithm comparison: extra clicks over {HORIZON} decisions ({N_SEEDS} seeds)")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "algorithm_comparison.png", dpi=DPI)
    plt.close(fig)


def plot_ope_validation() -> None:
    logging_probs = uniform_allocation(len(TRUE_CTRS)).tolist()
    target_probs = fixed_split_allocation(len(TRUE_CTRS), favored_arm=0, favored_share=0.9).tolist()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, estimator in zip(axes, ("ips", "snips"), strict=True):
        trials = run_ope_trials(
            true_ctrs=TRUE_CTRS,
            logging_probs=logging_probs,
            target_probs=target_probs,
            n_logged=2_000,
            n_trials=60,
            estimator=estimator,
            seed=0,
        )
        idx = np.arange(len(trials["estimates"]))
        covered = (trials["ci_lower"] <= trials["true_value"]) & (trials["true_value"] <= trials["ci_upper"])
        errors = np.abs(np.vstack([trials["estimates"] - trials["ci_lower"], trials["ci_upper"] - trials["estimates"]]))

        ax.errorbar(
            idx[covered],
            trials["estimates"][covered],
            yerr=errors[:, covered],
            fmt="o",
            color="#4C72B0",
            ecolor="#4C72B0",
            alpha=0.6,
            markersize=3,
            label="CI covers truth",
        )
        ax.errorbar(
            idx[~covered],
            trials["estimates"][~covered],
            yerr=errors[:, ~covered],
            fmt="o",
            color="#C44E52",
            ecolor="#C44E52",
            alpha=0.9,
            markersize=3,
            label="CI misses truth",
        )
        ax.axhline(trials["true_value"], color="black", linestyle="--", linewidth=1, label="true value")
        coverage_pct = 100 * covered.mean()
        ax.set_title(f"{estimator.upper()} — {coverage_pct:.0f}% of 95% CIs cover truth")
        ax.set_xlabel("Trial (independent logged dataset)")
        if ax is axes[0]:
            ax.set_ylabel("Estimated value")
        ax.legend(fontsize=7, loc="upper right")

    fig.suptitle("OPE validation: does the 95% CI actually contain the known true value?")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ope_validation.png", dpi=DPI)
    plt.close(fig)


def plot_sensitivity_sweep() -> None:
    def eg_builder(epsilon):
        def factory(metrics, rng):
            return EpsilonGreedyBandit(metrics, epsilon=epsilon).allocate()

        return factory

    epsilons = [0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8]
    results = sweep(epsilons, eg_builder, TRUE_CTRS, HORIZON, N_SEEDS)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(epsilons, [r["final_mean_regret"] for r in results], marker="o", color="#4C72B0")
    ax.set_xlabel("epsilon")
    ax.set_ylabel("Final mean cumulative regret")
    ax.set_title("Epsilon-greedy sensitivity: the exploration/exploitation trade-off")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "sensitivity_sweep.png", dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Running policies...")
    policy_results = run_all_policies()
    print("Plotting regret curves...")
    plot_regret_curves(policy_results)
    print("Plotting algorithm comparison...")
    plot_algorithm_comparison(policy_results)
    print("Plotting OPE validation...")
    plot_ope_validation()
    print("Plotting sensitivity sweep...")
    plot_sensitivity_sweep()
    print(f"Done. Figures written to {OUT_DIR}")
