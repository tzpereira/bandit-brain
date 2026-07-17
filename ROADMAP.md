# Bandit Brain — Roadmap

**Goal:** prove I can build a multi-armed-bandit system that a company would pay for — one that **works the way the real corporate equivalents already work**, not a drawer experiment. Revenue is not the point; *credibility* is. It may later slim down into a "quick bandit," but first it has to be indistinguishable, in mechanics and rigor, from how production bandit systems actually run.

**The path is linear — three milestones, each shippable on its own, each raising a strictly higher claim:**

| Milestone | Claim it earns | Objective it serves |
|---|---|---|
| **1 — Above-Average MVP** | "A correct bandit, built like a real system's loop." | Foundation — beats the typical portfolio project, but does not yet *prove* value. |
| **2 — The Hiring Portfolio** | "Here is a checkable number: −X% regret vs A/B, OPE recovers truth within Y%, live demo." | **The hiring objective: highly demonstrable + proves value.** This is the CV-ready point. |
| **3 — The Robust System** | "It behaves like production: cross-checked trust, safe rollout, operable, contextual." | The maximal version — only after Milestone 2 is live. |

Do not skip ahead: Milestone 2's value proof depends on Milestone 1's correct core, and Milestone 3's production claims mean nothing until Milestone 2 has shipped a checkable result.

**The bar is fidelity to real systems, not commercial polish.** Every design choice is anchored to how established tools do it, so the result is checkable against reality rather than against my own invented criteria:

| Reference system (real, in production) | What Bandit Brain mirrors from it |
|---|---|
| **Vowpal Wabbit** (contextual bandits) | The canonical **explore → log → learn** loop; log the *propensity of the chosen action*; IPS/DR for off-policy learning |
| **Azure Personalizer** (built on VW) | Split **Rank/Decide + Reward** APIs; **apprentice (shadow) mode**; offline evaluation *before* a policy is promoted |
| **ZOZO Open Bandit Pipeline** | Standardized OPE estimators + a public benchmark dataset used to **cross-check our numbers against an established implementation** |
| **Champion/challenger practice** | OPE-gated promotion, canary ramp, guardrail metrics, automatic revert |

**Two halves make a product.** A bandit that never sees the outcome of its own decisions is a report, not a product: (1) a **closed decision loop** — serve, log action + propensity, attribute reward, learn; and (2) a **trust layer** — counterfactual off-policy evaluation (OPE) that proves a policy beats what's running, with confidence intervals and honest caveats.

**Two ingestion modes, one schema.** The `propensity` field is filled by us or by the client; the product tracks provenance and *downgrades its trust claim accordingly* — refusing to call a biased number "audit-grade" is the core anti-snake-oil feature.

| Mode | Who decides | Who logs propensity | Trust guarantee |
|---|---|---|---|
| **Served** (`/decide`) | Bandit Brain | Bandit Brain | Unbiased OPE, audit-grade |
| **BYO-logs** (client serves) | Client system | Client sends it | Unbiased *if* client propensity is correct |
| **BYO, no propensity** | Client | nobody → assume uniform / estimate | Biased — labeled "best-effort, not auditable" |

Served (`/decide`) is the primary path (unbiased OPE for free, and the reference that validates the estimator); BYO-logs is the supported secondary path with explicit downgrading.

---

## The acceptance bar — "not a drawer experiment"

The project is only credible when a skeptical outsider can verify these *without trusting me*:

1. **The loop runs live end-to-end** — `decide → reward → learn` in the demo, not just batch scripts.
2. **OPE numbers are third-party-checkable** — our IPS/SNIPS/DR estimates reproduce a known-truth result in simulation *and* cross-check against the ZOZO OBP implementation on the same data (agreement within tolerance).
3. **No policy ships blind** — a new policy can only be promoted after passing an OPE gate + canary ramp; shadow mode is available to watch it first.
4. **Every decision is versioned and replayable** — decision → policy version + params + propensity, reconstructable from the audit log.
5. **Downside is capped** — guardrails enforce floors/caps at decision time; a kill-switch auto-reverts to a safe policy when a guardrail metric breaches.

Each phase's Definition of Done ladders up to these five. Anything not needed to clear this bar is a [non-goal](#non-goals).

---
---

## Milestone 1 — Above-Average MVP

*What already beats the typical portfolio project: a **correct** bandit and a loop that runs the way real CB systems run. It does **not** yet prove value — it is the prerequisite that makes the proof in Milestone 2 possible.*

### Phase 0 — Engineering Foundation ✅

- [x] Installable packages: `core/` (pure engine, zero FastAPI/DB imports), `api/`, `dashboard/`, `simulation/`
- [x] `uv` + `pyproject.toml` with a locked dependency set
- [x] `pytest` suite; `ruff` + `mypy` on `core/`; CI (lint → typecheck → tests) + `pre-commit`
- [x] Alembic migrations; `make seed` for local demo data

**Definition of Done:** `docker compose up` works from a clean clone, CI green, `core/` importable without a database. ✅

---

### Phase 1 — The Explore → Log → Learn Loop *(this is the product)*

The canonical shape every real CB system (VW, Personalizer) is built on. Without it there is no online learning and no honest evaluation.

#### 1.1 Correct, fractional, reproducible allocation

Today EG/UCB/TS hand 100% to one variant from a single draw — wrong and non-reproducible for batch allocation.

- [ ] Shared `BanditPolicy` interface: `allocate(state, config) -> Allocation` (distribution over arms), typed config per policy
- [ ] **Thompson Sampling:** allocate ∝ `P(arm is best)` via Monte Carlo over Beta posteriors (not one sample)
- [ ] **Epsilon-Greedy:** `(1 − ε)` to the empirical best, `ε / K` to each arm (deterministic given data)
- [ ] **UCB:** documented batch adaptation (top-arm with exploration floor, or normalized scores)
- [ ] **Softmax:** keep proportional form; document + test `tau`
- [ ] Seeded RNG everywhere: same inputs + seed → identical output

#### 1.2 Serve, log, and learn (the loop, VW/Personalizer-style)

- [ ] **`POST /decide`** (the *Rank* half): sample an arm from the current allocation, return it — the endpoint an ad server calls; enforce a documented **latency budget** (e.g. p99 < 50 ms)
- [ ] Every decision logged with: chosen arm, **propensity** `P(arm | state)`, `decision_source` (`served` | `byo`), **policy version + params**, `decision_id`, timestamp
- [ ] **`POST /reward`** (the *Reward* half): report an outcome attributed to a `decision_id` — the split-API contract real systems use
- [ ] **Learn:** policy state updates from attributed rewards on a defined cadence (batch or incremental); document the update model
- [ ] Data model: a per-decision table carrying propensity + provenance + policy version (Alembic migration); aggregated metrics become a derived view
- [ ] **BYO-logs mode:** `/ingest` accepts a client `propensity`; when absent, record `unlabeled` (assume-uniform) so OPE can downgrade rather than silently bias

#### 1.3 Bias controls + statistical correctness

- [ ] `min_allocation` / `max_allocation` floors and caps; "protect the champion" incumbent share
- [ ] Informative Beta priors for TS (seed from history so known-good arms start strong)
- [ ] Wilson-score CTR intervals (replace normal-approx SE); explicit zero-impression/zero-click handling
- [ ] Property tests (hypothesis): allocations sum to 1, respect floors/caps, permutation-equivariant

**Phase 1 Definition of Done:** `decide → reward → learn` runs end-to-end; decisions carry propensity + policy version and are replayable; all four policies produce fractional, reproducible, floor/cap-respecting allocations; `core/` coverage > 90%. *(Ladders to bars 1, 4.)*

> **Milestone 1 complete =** the loop works and the core is correct. Impressive as engineering, but a skeptic can't yet see *how much better than A/B* it is. That number is the entire job of Milestone 2 — go there next.

---
---

## Milestone 2 — The Hiring Portfolio

*The hiring objective, in full: **highly demonstrable + proves value.** This is where the checkable number on the README is born and the live demo goes online. Bandit value is counterfactual and therefore invisible in raw code — this milestone makes it visible and quantified. **This is the point at which the project belongs on the CV.***

### Phase 2 — Prove value on known truth *(the number that proves value)*

OPE done the way the field does it, and validated against a **known ground truth** so the headline number isn't self-graded. (Third-party cross-check against OBP and the DR estimator are deferred to Milestone 3 — IPS/SNIPS on a seeded environment is enough to *prove value*.)

#### 2.1 Off-policy evaluation (core estimators)

- [ ] **IPS** and **SNIPS** (self-normalized) estimators in `core/`, using logged propensities
- [ ] Confidence intervals on every estimate; report **effective sample size** and **propensity overlap** as reliability diagnostics
- [ ] **Provenance-aware trust:** audit-grade for `served`/known-propensity; explicitly *best-effort / biased* for `unlabeled`

#### 2.2 Prove the ruler isn't crooked (known ground truth)

- [ ] Synthetic Bernoulli environment with **known ground truth**, seedable; show IPS/SNIPS recover the true value (bias ≈ 0) with **correct CI coverage**
- [ ] Baselines: uniform A/B, oracle (always-best), fixed 90/10; **regret curves (mean ± CI over seeds)**; % traffic on true best arm; **extra clicks / saved cost vs. A/B** — this is the headline number
- [ ] Sensitivity sweeps over `epsilon`, `c`, `tau`, priors; with/without bias controls

**Phase 2 Definition of Done:** on a seeded known-truth environment, OPE recovers the true value with correct coverage, and the simulation yields a defensible headline number (regret vs A/B, extra clicks/saved cost). *(Ladders to bar 2.)*

---

### Phase 3 — Reproducible results + local polish *(make the value legible)*

- [ ] `notebooks/` (or a script) with the narrative: problem → method → results
- [ ] **One command regenerates every headline figure** (regret curves, OPE validation, algorithm comparison)
- [ ] **README "Results" section**: lead with plots + a table (algorithm × environment → regret vs. A/B, OPE recovery), then architecture, then quickstart
- [ ] Architecture diagram (mermaid): the explore-log-learn loop + OPE
- [ ] Split the 600-line `dashboard/app.py` into pages/modules; add an OPE/results page
- [ ] Answer the README's open questions (allocation shape, `select()` asymmetry, packaging)

**Phase 3 Definition of Done:** an unfamiliar dev goes from README to understanding the results and running the figures in ~10 minutes; every figure reproducible from a clean clone.

---

### Phase 4 — Public demo *(make the value clickable)*

- [ ] Deploy API + dashboard + Postgres to one host (Railway / Fly.io / Render — document the choice)
- [ ] Demo mode: seeded realistic dataset + read-only demo account; live `decide → reward → learn` visible
- [ ] Guardrails: auth rate limiting, upload size caps, nightly demo-data reset
- [ ] Fresh demo GIF/screenshots; `CONTRIBUTING.md`; tagged `v1.0.0` with a changelog
- [ ] Link from portfolio/CV with the headline metric (e.g. "−X% regret vs. A/B; OPE recovers truth within Y%")

**Phase 4 Definition of Done:** from a link, an outsider interacts with the live loop and reads the (checkable) results in under two minutes.

> **Milestone 2 complete =** a skeptical stranger clicks a link, pokes the live loop, and reads a checkable number in two minutes. **This is the hireable artifact.** Everything below is upside, not prerequisite — ship Milestone 2 before touching it.

---
---

## Milestone 3 — The Robust System

*The maximal version — makes it behave, not just look, like production. Start only after Milestone 2 is live. Each phase raises the "this is a real system" claim; each is independently valuable and can be prioritized or dropped.*

### Phase 5 — Full trust layer, cross-checked *(the ZOZO part)*

Take the trust layer from "recovers known truth" to "matches an established third-party implementation."

- [ ] **Doubly-Robust (DR)** estimator: unbiased if *either* propensity or reward model is right — the safety net
- [ ] **Cross-check against ZOZO OBP**: run the same estimators on the same logged data through OBP and confirm agreement within tolerance — the third-party check that makes the numbers believable
- [ ] Extend the known-truth validation (Phase 2.2) to cover DR; add the OBP agreement result to the README Results table

**Phase 5 Definition of Done:** OPE recovers known truth *and* matches OBP on shared data within tolerance; DR is available for the biased/`unlabeled` case. *(Completes bar 2.)*

---

### Phase 6 — Safe rollout & policy lifecycle *(the production hallmark)*

What actually separates a real system from a demo: you never swap policies blindly. Mirrors Personalizer's apprentice mode and standard champion/challenger practice.

- [ ] **Shadow / apprentice mode:** a challenger policy logs what it *would* have decided alongside the live champion, without affecting traffic
- [ ] **OPE-gated promotion:** a challenger can only become champion after its OPE estimate beats the champion's with a CI that clears a threshold
- [ ] **Canary ramp:** promote by gradually shifting traffic share (e.g. 5% → 25% → 100%), not all at once
- [ ] **Guardrail metrics + kill-switch:** define guardrails (e.g. CTR floor, cost ceiling); auto-revert to the last safe policy on breach
- [ ] Policy registry: versioned policies with state (`shadow` → `canary` → `champion` → `retired`) and the audit trail linking every decision to its version

**Phase 6 Definition of Done:** a challenger can be shadowed, evaluated, canaried, promoted, and auto-reverted — end to end, observable in the dashboard. *(Ladders to bars 3, 5.)*

---

### Phase 7 — Operable day-to-day

The minimum plumbing a real tenant needs; deliberately light on scale (this isn't a revenue SaaS).

- [ ] Experiments as first-class resources with a lifecycle (`draft` → `running` → `stopped`), not name-keyed rows
- [ ] **Idempotent ingestion** + late-arriving rewards (upserts keyed by decision/event id)
- [ ] Auth hardening: refresh tokens, rate limiting, password policy
- [ ] Delete routes take explicit filters (today they wipe *all* of a tenant's records — dangerous)
- [ ] Connection pooling (today a connection is opened/closed per call) + keyset pagination on list routes
- [ ] Structured logging + a health/metrics endpoint

**Phase 7 Definition of Done:** multiple experiments run concurrently with lifecycle states; ingestion is safe under retries and late data; no route can wipe a tenant by accident; the API stays responsive under load.

---

### Phase 8 — Contextual bandits *(optional / stretch)*

Only after everything above is solid. The real reference here is VW's `--cb_explore_adf`. Uses the `device` / `location` / `user_segment` / `hour` context already stored.

- [ ] Feature pipeline (context → features), shared train/serve
- [ ] Baseline: per-segment independent bandits; then **LinUCB** (disjoint) in `core/`
- [ ] `/decide` and OPE become context-conditional; dashboard per-segment allocation heatmap
- [ ] Simulation where the best arm depends on context — contextual beats context-blind, evaluated with the same OPE machinery

**Phase 8 Definition of Done:** contextual policies outperform context-blind ones on heterogeneous environments, exposed end-to-end and evaluated identically.

---
---

## Non-goals

Out of scope on purpose. Each is interview-ready as "I scoped this out so the loop + trust + safe-rollout story stays sharp — it doesn't make the system more *credible as production*."

- **Real-time / streaming beyond the batch + `/decide` + `/reward` API.** No configurable live feed; the commitment is a correct decision loop + offline evaluation, not stream processing.
- **Non-stationarity & drift modeling** (sliding windows, discounted TS/UCB, change-point detection). *(Operational late-data handling is in Phase 7; drift-aware algorithms are not.)*
- **Delayed-reward modeling** (lag distributions, imputation). The operational upsert of late rewards is in Phase 7; modeling the delay is not.
- **Budget-aware / ROI allocation** (spend plans, CPC/value objectives, currency floors). A separate product direction — and the reason this is a portfolio capability proof, not a drop-in tool for optimizing your own ad spend.
- **Revenue-grade SaaS ops** (billing, multi-region, autoscaling, SSO). This is a capability proof, not a business; tenancy stays light.

---

## The linear path, at a glance

1. **Milestone 1 (Phase 0–1)** — build the correct core + the explore→log→learn loop. *Above-average, but not yet proof.*
2. **Milestone 2 (Phase 2–4)** — simulate against known truth to mint the headline number, make the results reproducible and legible, deploy the live demo. **Stop here and put it on the CV: this is the demonstrable, value-proving artifact.**
3. **Milestone 3 (Phase 5–8)** — cross-check the trust layer against OBP, add safe rollout, make it operable, then contextual. *Each phase is independent upside; prioritize or drop per appetite.*

A live demo of a correct core with a cross-checked headline number (end of Milestone 2) beats an unfinished maximal scope every time. Milestone 3 is what you reach for once the hiring artifact is already online.
