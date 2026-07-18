from pathlib import Path

import streamlit as st
from config import API_URL
from session import require_login

require_login(API_URL)

st.set_page_config(page_title="Bandit Brain - Results", layout="wide")

st.title("📊 Simulation Results")
st.caption(
    "Reproducible proof, not a live view: a synthetic 3-arm environment with known true CTRs "
    "(0.030 / 0.055 / 0.038), 3,000 decisions, averaged over 50 seeds. Regenerate with "
    "`make report` (text) and `make figures` (these plots) — see ROADMAP.md Phase 2."
)

FIGURES_DIR = Path(__file__).resolve().parent.parent.parent / "public" / "figures"


def show_figure(filename: str, caption: str) -> None:
    path = FIGURES_DIR / filename
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"`{filename}` not found. Run `make figures` to generate it.")


st.header("Every real policy beats a fixed A/B split")
show_figure("algorithm_comparison.png", "Extra clicks vs. uniform A/B/C over 3,000 decisions")

st.dataframe(
    {
        "Algorithm": [
            "Thompson Sampling",
            "Epsilon-greedy",
            "Softmax",
            "UCB",
            "Oracle (ceiling)",
            "Uniform A/B/C (baseline)",
            "Fixed 90/10",
        ],
        "Extra clicks vs. uniform A/B/C": ["+28.28", "+24.90", "+18.00", "+4.14", "—", "—", "worse than uniform"],
        "Final regret (95% CI)": [
            "15.24 [12.58, 17.89]",
            "17.39 [12.48, 22.29]",
            "24.22 [21.92, 26.52]",
            "38.10 [37.73, 38.47]",
            "0.00",
            "41.99 [41.84, 42.15]",
            "69.99 [69.89, 70.09]",
        ],
        "% traffic on true best arm": ["74.3%", "70.8%", "60.3%", "39.1%", "100.0%", "33.3%", "5.1%"],
    },
    use_container_width=True,
    hide_index=True,
)
st.caption(
    "A fixed split can lose to plain uniform A/B if it happens to favor the wrong variant — "
    'a real failure mode of static "control gets 90%" splits, and the reason adaptive allocation exists.'
)

st.header("Cumulative regret over time")
show_figure("regret_curves.png", "Shaded = 95% CI over seeds. Sublinear curves are what learning looks like.")

st.header("Off-policy evaluation recovers the known truth")
show_figure(
    "ope_validation.png",
    "60 independent trials, each logging 2,000 decisions under a uniform logging policy, "
    "evaluating a fixed 90/10 target policy via IPS/SNIPS.",
)
st.dataframe(
    {
        "Estimator": ["IPS", "SNIPS"],
        "True value": ["0.0316", "0.0316"],
        "Mean bias": ["+0.00023", "-0.00001"],
        "95% CI coverage (target: 95%)": ["92.0%", "92.5%"],
    },
    use_container_width=True,
    hide_index=True,
)

st.header("Sensitivity sweep")
show_figure("sensitivity_sweep.png", "Epsilon-greedy's epsilon traces the exploration/exploitation trade-off.")
