# Changelog

Notable changes to this project, loosely following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). See [ROADMAP.md](ROADMAP.md) for what's planned/in-progress.

## [Unreleased]

### Milestone 1 — correct core + the serve/log/learn loop

**Added**
- Shared `BanditPolicy` interface: all four policies (epsilon-greedy, UCB, Thompson Sampling, softmax) now return fractional, reproducible allocations instead of winner-take-all
- `POST /decide` and `POST /reward` — the serve → log → learn loop, with propensity and policy version logged per decision; served traffic feeds back into `/metrics` for the next `/recommend` call
- Bias controls: `min_allocation`/`max_allocation` floors/caps (water-filling projection), a "protect the champion" incumbent floor, and informative Beta priors for Thompson Sampling
- Wilson-score confidence intervals for CTR, replacing a normal approximation that collapsed to `[0, 0]` at zero clicks
- Hypothesis-based property tests for allocation invariants (sum-to-1, floor/cap respect, permutation-equivariance) — caught a real bug in the first version of the floor/cap projection

### Milestone 2 — prove value, make it legible, guard the public demo

**Added**
- `core/ope.py`: IPS/SNIPS off-policy evaluation with confidence intervals, effective sample size, propensity overlap, and provenance-aware trust levels
- `simulation/`: a synthetic Bernoulli-arm environment with known ground truth, baselines (uniform A/B, oracle, fixed split), an online policy runner reusing the production policy code, OPE coverage validation against the known truth, and hyperparameter sensitivity sweeps
- `make report` / `make figures`: reproducible headline numbers and plots — regret curves with CI, algorithm comparison, OPE validation, sensitivity sweep
- README "Results" section (plots + tables, leading the page) and a mermaid architecture diagram of the serve/log/learn loop + OPE
- Dashboard split from a single 690-line script into pages/modules, plus a new Results page mirroring the README
- Guardrails for a public deployment: a hard-guarded read-only demo account (`users.is_demo` + 403 on write routes), rate limiting on `/signup`/`/login`, upload size caps, and a demo-data reset script

**Fixed**
- `scripts/seed.py` no longer falls back to a publicly-known default password against a non-local target

### Earlier

The original interview take-home: FastAPI + Streamlit + PostgreSQL bandit service (ingest, recommend, JWT auth, dashboard). See `git log` for the full history.
