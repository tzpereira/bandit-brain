# Bandit Brain — Roadmap

Goal: evolve Bandit Brain from an interview take-home into a portfolio-grade experimentation platform where the algorithms are **mathematically correct**, their benefit is **empirically proven** (simulation + backtesting), and the engineering is **production-quality**.

Positioning: Data Science depth on top of solid engineering. Streamlit dashboard stays. Public live demo at the end.

How to use this file: check items off as they land (`[x]`). Each phase has a **Definition of Done** — don't start the next phase's core work until it's met. Phases 3–5 are independent of each other and can be reordered.

---

## Phase 0 — Engineering Foundation

Everything after this phase must land with tests and pass CI.

- [x] Restructure the repo into installable packages: `core/` (pure bandit engine, zero FastAPI/DB imports), `api/` (FastAPI layer), `dashboard/`, `simulation/`
- [x] Adopt `uv` + `pyproject.toml` with pinned/locked dependencies (replace loose `requirements.txt`)
- [x] Set up `pytest` with a first smoke-test suite (import + docker-compose healthcheck)
- [x] Add `ruff` (lint + format) and `mypy` on the `core/` package
- [x] GitHub Actions CI: lint → typecheck → tests on every PR/push
- [x] Add `pre-commit` hooks mirroring CI
- [x] Database migrations with Alembic (replace raw `schema.sql` bootstrap)
- [x] Seed script for local dev data (`make seed`)

**Definition of Done:** `docker compose up` works from a clean clone, CI is green, `core/` is importable and testable without a database.

---

## Phase 1 — Correct Core Algorithms + Exploration/Exploitation Bias

Fix the conceptual flaws in the current implementations. This is the heart of the project — and directly addresses the interview feedback (no way to bias budget toward known-good ads).

### 1.1 Fractional allocations (fix the all-or-nothing bug)

Today EG/UCB/TS return 100% to one variant and 0% to the rest from a single random draw. For daily batch allocation this is wrong and non-reproducible.

- [ ] **Thompson Sampling**: allocate proportional to `P(variant is best)` estimated via Monte Carlo over posterior samples (e.g. 10k draws), not a single sample
- [ ] **Epsilon-Greedy**: allocate `(1 - ε)` to the empirical best and `ε / K` to each variant (deterministic given data)
- [ ] **UCB**: deterministic top-arm allocation with explicit exploration floor, or normalized UCB scores — document the chosen batch adaptation and why
- [ ] **Softmax**: keep proportional form; make `tau` semantics documented and tested (already the closest to correct)
- [ ] All algorithms accept a seeded RNG (`numpy.random.Generator`) — same inputs + seed → same output
- [ ] Shared `BanditPolicy` interface: `allocate(stats, config) -> list[Allocation]` with typed dataclasses/pydantic models

### 1.2 Exploration/exploitation bias controls (the interview gap)

- [ ] `min_allocation` / `max_allocation` floors and caps per variant (e.g. "never give a variant less than 5% or more than 80%")
- [ ] `exploitation_bias` parameter: sharpen allocations toward proven winners (temperature on the P(best) distribution / epsilon decay schedule)
- [ ] Informative Beta priors for TS: seed a variant's prior from historical performance so known-good ads start strong instead of at Beta(1,1)
- [ ] "Protect the champion" mode: guarantee the incumbent variant a configurable share while challengers are explored
- [ ] Expose all bias controls in the `/recommend` API and dashboard

### 1.3 Statistical correctness

- [ ] CTR confidence intervals via Wilson score (replace normal-approximation SE for small samples)
- [ ] Handle zero-impression and zero-click variants explicitly in every algorithm (no silent `1.0` scores)
- [ ] Unit tests against closed-form/known results (e.g. TS with overwhelming evidence → ~100% to winner; symmetric arms → ~uniform)
- [ ] Property-based tests (hypothesis): allocations always sum to 1, respect floors/caps, are permutation-equivariant

**Definition of Done:** all four policies produce fractional, reproducible, floor/cap-respecting allocations; bias controls demonstrably shift budget toward proven variants; `core/` test coverage > 90%.

---

## Phase 2 — Prove It Works: Simulation & Backtesting

The portfolio centerpiece. Nothing says "the algorithms really work" like regret curves against baselines.

### 2.1 Simulation framework (`simulation/` package)

- [ ] Synthetic environment: Bernoulli arms with configurable true CTRs, arrival volumes, and noise
- [ ] Environment variants: stationary, drifting CTRs, abrupt change-points, hour-of-day seasonality
- [ ] Simulation runner: policy × environment × horizon × n_seeds → results dataframe (parallelized)
- [ ] Baselines: uniform A/B split, oracle (always-best), fixed 90/10 split

### 2.2 Evaluation metrics & analysis

- [ ] Cumulative regret and per-period regret curves (mean ± CI over seeds)
- [ ] % of traffic on the true best arm over time
- [ ] Business framing: extra clicks / saved cost vs uniform A/B at equal traffic
- [ ] Sensitivity analysis: sweep `epsilon`, `c`, `tau`, priors — show tuning tradeoffs
- [ ] Show the effect of the bias controls: with/without floors and informative priors (the interview-feedback money-shot)

### 2.3 Offline replay on real data

- [ ] Replay evaluation on logged data (Li et al. replay method) using the example CSV / uploaded datasets
- [ ] `POST /backtest` endpoint (or CLI) that runs a policy over an experiment's history and reports what-if performance

### 2.4 Publish the evidence

- [ ] Analysis notebook(s) in `notebooks/` with narrative: problem → method → results
- [ ] Export headline plots (regret curves, algorithm comparison) as images embedded in the README
- [ ] "Results" section in README with a table: algorithm × environment → regret vs A/B baseline

**Definition of Done:** one command reproduces every figure; README shows TS/UCB beating uniform A/B with numbers; bias controls shown reducing cost of exploration on known-good arms.

---

## Phase 3 — Contextual Bandits

Use the context data (`device`, `location`, `user_segment`, `hour`) that the schema stores but the algorithms currently ignore.

- [ ] Feature pipeline: context JSONB → model features (one-hot/target encoding), shared between training and serving
- [ ] Baseline: per-segment independent bandits (separate Beta posteriors per `device × segment` cell) — simple, interpretable
- [ ] **LinUCB** (disjoint model) implementation in `core/`
- [ ] Contextual Thompson Sampling (Bayesian linear/logistic regression posterior)
- [ ] Extend `/recommend` to accept a context and return context-conditional allocations
- [ ] Simulation: environments where the best arm depends on context — show contextual policies beating context-blind ones
- [ ] Dashboard: allocation heatmap per segment (which variant wins where)
- [ ] Notebook: "when does context help?" analysis

**Definition of Done:** contextual policies demonstrably outperform context-blind ones on heterogeneous environments in simulation, exposed end-to-end (API + dashboard).

---

## Phase 4 — Non-Stationarity & Delayed Rewards

Real ad performance drifts and conversions arrive late. Handle both.

### 4.1 Non-stationary environments

- [ ] Sliding-window statistics (configurable lookback) for all policies
- [ ] Discounted Thompson Sampling / discounted UCB (exponential decay of evidence, configurable half-life)
- [ ] Optional change-point detection (e.g. Page-Hinkley) that resets/inflates uncertainty on drift
- [ ] Simulation: drifting and change-point environments — show discounted variants recovering faster than vanilla
- [ ] Expose `window` / `decay` parameters in API + dashboard

### 4.2 Delayed rewards

- [ ] Model reward delay in the simulator (clicks/conversions arriving with a lag distribution)
- [ ] Ingestion supports late-arriving events updating past dates (idempotent upserts)
- [ ] Delay-aware correction: down-weight recent incomplete periods or use expected-delay imputation — document the chosen approach
- [ ] Simulation: show naive policies over-penalizing recent variants vs the delay-aware version

**Definition of Done:** simulations demonstrate faster adaptation to drift and unbiased handling of reward lag, with parameters exposed and documented.

---

## Phase 5 — Budget-Aware Allocation

Move from "share of traffic" to "share of money" — the framing ad platforms actually care about.

- [ ] Objective switch: optimize clicks (CTR), cost-efficiency (CPC), or value (configurable reward definition)
- [ ] Budget constraint: allocate a daily budget across variants given cost-per-impression estimates
- [ ] Constrained allocation: floors/caps in currency, not just percentage
- [ ] ROI-based bandit: reward = value − cost, with uncertainty on both
- [ ] Simulation: budget scenarios showing higher total return vs proportional-traffic allocation
- [ ] API: `/recommend` accepts `budget` and `objective`; response includes per-variant spend

**Definition of Done:** given a budget and an objective, the platform returns a spend plan, and simulation shows it beats naive traffic-proportional spending.

---

## Phase 6 — Platform Hardening (API + Dashboard)

- [ ] API redesign: experiments as first-class resources (`/experiments/{id}/recommendations`), consistent REST semantics, keyset pagination
- [ ] Versioned API (`/v1`), typed error responses, request IDs
- [ ] Auth hardening: refresh tokens, password policy, rate limiting on auth routes
- [ ] Delete routes take explicit filters (today they delete without payload — dangerous)
- [ ] Structured logging (JSON) + basic metrics endpoint (Prometheus-style)
- [ ] Async DB access or connection pooling review; N+1 / full-scan audit on repositories
- [ ] Integration test suite against a real Postgres (testcontainers) covering every route
- [ ] Dashboard refactor: split 635-line `app.py` into pages (`Experiments`, `Recommendations`, `Simulation Lab`, `Backtest`) and modules
- [ ] Dashboard "Simulation Lab" page: pick environment + policies, run, see regret curves interactively
- [ ] Load/perf sanity check: ingest 1M rows, recommend under 500ms

**Definition of Done:** every endpoint integration-tested, dashboard modular, an unfamiliar dev can navigate the codebase from the README in 10 minutes.

---

## Phase 7 — Public Demo & Portfolio Polish

- [ ] Deploy API + dashboard + Postgres to Railway/Fly.io/Render (pick one, document the choice)
- [ ] Demo mode: seeded realistic dataset + read-only demo account (or auto-login) so recruiters explore with zero setup
- [ ] Nightly reset job for demo data; abuse guardrails (rate limits, upload size caps)
- [ ] README rewrite: lead with the problem and the **results** (plots, numbers), then architecture diagram, then quickstart; keep API reference in `docs/`
- [ ] Fresh demo GIF/screenshots of the new dashboard
- [ ] Architecture diagram (excalidraw/mermaid) in README
- [ ] Write-up (blog post or `docs/DESIGN.md`): "Building a bandit platform that actually reduces regret" — includes the interview-feedback story and how bias controls solve it
- [ ] Add `CONTRIBUTING.md`, issue templates, tagged `v1.0.0` release with changelog
- [ ] Link from portfolio/LinkedIn/CV with the headline metric (e.g. "−X% regret vs A/B testing in simulation")

**Definition of Done:** a recruiter can go from a link to interacting with a live demo and reading results in under two minutes.

---

## Suggested order & scope guardrails

1. Phases **0 → 1 → 2** are the critical path — after Phase 2 the project is already a strong portfolio piece.
2. Phases **3, 4, 5** are independent; pick the next one based on energy/interviews (contextual bandits have the highest DS-interview value).
3. Phases **6 → 7** close it out. Ship the demo even if 3–5 are partially done — a live demo of a correct core beats an unfinished maximal scope.
