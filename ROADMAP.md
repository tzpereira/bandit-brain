# Bandit Brain — Roadmap

**Goal:** turn Bandit Brain into a portfolio-grade project where the bandit algorithms are **mathematically correct**, their benefit is **empirically proven offline**, and the engineering is clean. Scope is deliberately lean — depth over breadth.

**Thesis:** there is no configurable real-time feed here (the HTTP API is the only live surface), so the project doesn't pretend to be a streaming platform. Instead it goes **top-tier on offline evaluation** — rigorous backtesting and simulation that prove, with numbers and reproducible figures, that these policies beat a fixed A/B split on logged data. That rigor *is* the portfolio piece.

**How to read this file:** check items off as they land (`[x]`). Each phase has a **Definition of Done** — don't start the next phase until it's met. Phases are ordered by priority; ship even if the optional phase is skipped.

**Scope discipline:** anything not needed to prove the thesis is a non-goal. See [Non-goals](#non-goals) at the bottom — that list is a feature, not an omission.

---

## Phase 0 — Engineering Foundation ✅

Done. Everything after this lands with tests and passes CI.

- [x] Installable packages: `core/` (pure engine, zero FastAPI/DB imports), `api/`, `dashboard/`, `simulation/`
- [x] `uv` + `pyproject.toml` with a locked dependency set
- [x] `pytest` suite (core policies, ingest validation, API smoke)
- [x] `ruff` (lint + format) and `mypy` on `core/`
- [x] GitHub Actions CI (lint → typecheck → tests) + mirrored `pre-commit` hooks
- [x] Alembic migrations; `make seed` for local demo data

**Definition of Done:** `docker compose up` works from a clean clone, CI is green, `core/` is importable and testable without a database. ✅

---

## Phase 1 — Correct Core Algorithms + Bias Controls

The substance. Fix the conceptual flaws in the current implementations and add the one control the original interview flagged as missing: biasing budget toward known-good variants.

### 1.1 Fractional, reproducible allocations

Today EG/UCB/TS hand 100% of traffic to a single variant from one random draw — wrong and non-reproducible for daily batch allocation.

- [ ] Shared `BanditPolicy` interface: `allocate(metrics, config) -> list[Allocation]`, typed config per policy
- [ ] **Thompson Sampling:** allocate proportional to `P(variant is best)` via Monte Carlo over the Beta posteriors (e.g. 10k draws), not a single sample
- [ ] **Epsilon-Greedy:** `(1 − ε)` to the empirical best, `ε / K` to each variant (deterministic given data)
- [ ] **UCB:** documented batch adaptation — top-arm with an explicit exploration floor, or normalized UCB scores
- [ ] **Softmax:** keep the proportional form; document + test `tau` semantics (already closest to correct)
- [ ] Seeded RNG (`numpy.random.Generator`) everywhere: same inputs + seed → identical output

### 1.2 Bias controls (the interview gap)

- [ ] `min_allocation` / `max_allocation` floors and caps per variant
- [ ] Informative Beta priors for TS: seed a variant's prior from history so known-good variants start strong instead of at `Beta(1,1)`
- [ ] "Protect the champion" mode: guarantee the incumbent a configurable share while challengers are explored
- [ ] Expose the bias controls in `/recommend` and the dashboard

### 1.3 Statistical correctness

- [ ] Wilson-score CTR confidence intervals (replace the normal-approximation SE for small samples)
- [ ] Explicit handling of zero-impression / zero-click variants in every policy (no silent `1.0` scores)
- [ ] Unit tests against known results (overwhelming evidence → ~100% to winner; symmetric arms → ~uniform)
- [ ] Property tests (hypothesis): allocations sum to 1, respect floors/caps, are permutation-equivariant

**Definition of Done:** all four policies produce fractional, reproducible, floor/cap-respecting allocations; bias controls demonstrably shift budget toward proven variants; `core/` coverage > 90%.

---

## Phase 2 — Backtesting & Simulation (the centerpiece)

Top-tier offline evaluation. This is where the project earns its keep: prove the policies work on logged data and in controlled simulation, with reproducible evidence.

### 2.1 Offline replay on logged data (the headline)

The gold standard for evaluating a bandit without deploying it.

- [ ] Implement the **replay / rejection-sampling estimator** (Li et al., 2011) over logged events: step through history, only "accept" a logged event when the policy's choice matches the logged variant, accumulate reward on accepted events
- [ ] Document the core assumption (logging policy ≈ uniform over variants) and what breaks if it doesn't hold
- [ ] Report effective sample size / acceptance rate so the estimate's reliability is visible, not hidden
- [ ] `banditbrain.simulation` API + a `POST /backtest` endpoint (or CLI): run a policy over an experiment's history, return what-if reward vs. what actually happened
- [ ] Run it on the example CSV and any uploaded dataset

### 2.2 Simulation environment + baselines

- [ ] Synthetic Bernoulli-arm environment: configurable true CTRs, arrival volumes, seedable
- [ ] Runner: policy × environment × horizon × n_seeds → tidy results dataframe
- [ ] Baselines to beat: uniform A/B split, oracle (always-best), fixed 90/10 split

### 2.3 Evaluation metrics

- [ ] Cumulative and per-period **regret** curves (mean ± CI over seeds)
- [ ] % of traffic on the true best arm over time
- [ ] Business framing: extra clicks / saved cost vs. uniform A/B at equal traffic
- [ ] Sensitivity sweeps over `epsilon`, `c`, `tau`, and priors — the tuning story
- [ ] With/without the Phase 1 bias controls — quantify the interview-feedback fix

**Definition of Done:** one command reproduces every figure with a fixed seed; the replay estimator runs on real logged data and reports its own reliability; simulation shows TS/UCB beating uniform A/B with numbers.

---

## Phase 3 — Contextual Bandits *(optional / stretch)*

Only after Phases 1–2 are solid. Uses the `device` / `location` / `user_segment` / `hour` context the schema already stores but the algorithms ignore. Highest data-science-interview value; skip without guilt if time is short.

- [ ] Feature pipeline: context → model features (one-hot / target encoding), shared train/serve
- [ ] Baseline: per-segment independent bandits (separate Beta posteriors per `device × segment`) — simple, interpretable
- [ ] **LinUCB** (disjoint model) in `core/`
- [ ] Extend `/recommend` to accept a context and return context-conditional allocations
- [ ] Simulation where the best arm depends on context — show contextual beating context-blind
- [ ] Dashboard: per-segment allocation heatmap (which variant wins where)

**Definition of Done:** contextual policies demonstrably outperform context-blind ones on heterogeneous environments in simulation, exposed end-to-end (API + dashboard).

---

## Phase 4 — Reproducible Results + Local Polish *(portfolio deliverable 1)*

Make the evidence undeniable and the repo navigable.

- [ ] `notebooks/` (or a script) with the narrative: problem → method → results
- [ ] One command regenerates every headline figure (regret curves, algorithm comparison, replay results)
- [ ] **README "Results" section**: lead with the plots and a table (algorithm × environment → regret vs. A/B), then architecture, then quickstart
- [ ] Architecture diagram (mermaid) in the README
- [ ] Delete routes take explicit filters (today they wipe all of a user's records with no payload — dangerous)
- [ ] Split the 600-line `dashboard/app.py` into pages/modules
- [ ] Answer the three open questions in the README (all-or-nothing allocation, `select()` asymmetry, packaging)

**Definition of Done:** an unfamiliar dev goes from README to understanding the results and running the figures in ~10 minutes; every figure is reproducible from a clean clone.

---

## Phase 5 — Public Demo *(portfolio deliverable 2)*

A recruiter clicks a link and explores a working instance with zero setup.

- [ ] Deploy API + dashboard + Postgres to one host (Railway / Fly.io / Render — document the choice)
- [ ] Demo mode: seeded realistic dataset + read-only demo account (or auto-login)
- [ ] Guardrails: rate limiting on auth routes, upload size caps, nightly demo-data reset
- [ ] Fresh demo GIF/screenshots of the current dashboard
- [ ] `CONTRIBUTING.md` + a tagged `v1.0.0` release with a changelog
- [ ] Link from portfolio/CV with the headline metric (e.g. "−X% regret vs. A/B in simulation")

**Definition of Done:** from a link, a recruiter interacts with the live demo and reads the results in under two minutes.

---

## Non-goals

Explicitly out of scope for this lean version. Each is defensible and interview-ready as "I scoped this out on purpose because the offline-evaluation story is what proves the algorithms work — these would add surface area without strengthening that thesis."

- **Real-time / streaming ingestion** beyond the batch HTTP API. There's no configurable real-time feed; the project commits to rigorous *offline* evaluation instead.
- **Non-stationarity & drift handling** (sliding windows, discounted TS/UCB, change-point detection). Interesting, but a second research thread on top of an already-complete story.
- **Delayed-reward modeling** (lagged conversions, idempotent upserts of late events). Same reason.
- **Budget-aware / ROI allocation** (spend plans, CPC/value objectives, currency floors). A whole product direction of its own.
- **Heavy platform hardening** (API versioning, refresh tokens, keyset pagination, Prometheus metrics, testcontainers integration suite). The minimum safety items (delete filters, auth rate limiting) are folded into Phases 4–5; the rest is enterprise polish beyond a portfolio piece.

---

## Suggested order

1. **Phase 1 → 2** is the critical path. After Phase 2 the project is already a strong portfolio piece.
2. **Phase 3** is optional — do it only if the core + backtesting are solid and there's appetite for the highest-DS-value extension.
3. **Phase 4 → 5** close it out. Ship the demo even if Phase 3 is skipped — a live demo of a correct, empirically-validated core beats an unfinished maximal scope.
