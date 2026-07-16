<p align="center">
  <img src="public/logo.png" alt="Bandit Brain logo" width="180"/>
</p>

# Bandit Brain

Decide how to split traffic across the variants of an online experiment using multi-armed bandit algorithms instead of a fixed A/B split. Bandit Brain is a pure Python bandit engine (`core`) with an optional FastAPI service and a Streamlit dashboard on top.

[![CI](https://github.com/tzpereira/bandit-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/tzpereira/bandit-brain/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.1.0-lightgrey)

![Demo](public/demo.gif)

---

## Why / when to use it

- **You run ads or landing-page variants and want to shift budget toward winners automatically.** Feed daily impressions/clicks per variant and get a recommended allocation for the next day.
- **You want to compare bandit strategies on your own data.** Four policies (epsilon-greedy, UCB, Thompson sampling, softmax) share one interface, so you can swap them on the same metrics and see how allocation changes.
- **You need the algorithms without the stack.** The `banditbrain.core` package depends only on `numpy` and `pydantic` — import it into your own service, no database or web server required.

---

## Installation

Dependencies are managed with [uv](https://docs.astral.sh/uv/). The package is not published to PyPI — install from source.

```bash
git clone https://github.com/tzpereira/bandit-brain.git
cd bandit-brain

# Core engine only (numpy + pydantic)
uv sync

# Everything (API + dashboard + dev tools)
uv sync --all-extras        # or: make install
```

Optional dependency groups defined in `pyproject.toml`: `api` (FastAPI, uvicorn, psycopg2, PyJWT, bcrypt, Alembic) and `dashboard` (Streamlit, Plotly, Polars).

---

## Quickstart

Use the core engine directly — no server, no database. This runs as-is:

```python
from banditbrain.core.models import Metric
from banditbrain.core.policies import ThompsonSamplingBandit

# One Metric per variant. ctr = clicks / impressions.
metrics = [
    Metric(variant_name="A", impressions=1000, clicks=120, total_cost=1.0,
           device="mobile", location="BRA", user_segment="new_user",
           ctr=0.120, ctr_se=0.010, ctr_ci_lower=0.100, ctr_ci_upper=0.140),
    Metric(variant_name="B", impressions=950, clicks=80, total_cost=0.9,
           device="desktop", location="USA", user_segment="returning_user",
           ctr=0.084, ctr_se=0.009, ctr_ci_lower=0.066, ctr_ci_upper=0.102),
]

bandit = ThompsonSamplingBandit(metrics, experiment_name="homepage_test", date="2026-01-01")
for allocation in bandit.get_allocation():
    print(allocation.variant_name, allocation.allocated_pct, allocation.date)
# A 1.0 2026-01-02
# B 0.0 2026-01-02
```

Every policy exposes the same `get_allocation()` method returning a list of `Allocation` objects whose `allocated_pct` values sum to `1.0`. The allocation `date` is always the day **after** the input `date` (next-day forecast).

To run the full stack instead (API + dashboard + PostgreSQL):

```bash
cp .env.example .env
docker compose up --build      # or: make up
make seed                      # optional: load demo data
```

- API: <http://localhost:8000> (OpenAPI docs at `/docs`)
- Dashboard: <http://localhost:8501>

---

## Core concepts: the four policies

All four take a `list[Metric]` and produce a `list[Allocation]`. They differ in how they turn observed click-through rates (CTR) into an allocation.

| Strategy | Class | Tuning param | Allocation shape | Choose it when |
|---|---|---|---|---|
| Epsilon-greedy | `EpsilonGreedyBandit` | `epsilon` (0–1, default 0.1) | 100% to one variant | You want the simplest exploration/exploitation knob. |
| UCB | `UCBBandit` | `c` (>0, default 2.0) | 100% to one variant | You want exploration driven by uncertainty, not a fixed rate. |
| Thompson sampling | `ThompsonSamplingBandit` | — | 100% to one variant | Data is sparse/uncertain and you want a Bayesian approach. |
| Softmax | `SoftmaxBandit` | `tau` (>0, default 0.1) | Proportional across all variants | You want every variant to keep a share of traffic. |

**Epsilon-greedy.** With probability `epsilon` it picks a variant uniformly at random (explore); otherwise it picks the one with the highest observed CTR (exploit). Simple and fast, but exploration is a fixed rate that doesn't adapt — high `epsilon` wastes traffic, low `epsilon` can lock onto a false winner early.

**UCB (Upper Confidence Bound).** Scores each variant as `ctr + c * sqrt(ln(total_impressions) / impressions)` and picks the highest. Under-sampled variants get an optimism bonus, so exploration is directed at what's least certain rather than random. Variants with zero impressions are treated as maximally promising (`score = 1.0`). `c` controls how aggressively it explores.

**Thompson sampling.** For each variant it draws a sample from a `Beta(1 + clicks, 1 + impressions − clicks)` posterior and picks the variant with the highest draw. Naturally balances exploration and exploitation and handles small samples gracefully, with no rate to tune. Because it samples, the choice is stochastic across calls.

**Softmax.** Converts CTRs into a probability distribution with a numerically stable softmax at temperature `tau` and allocates traffic proportionally: `p_i = exp(ctr_i / tau) / Σ_j exp(ctr_j / tau)`. Unlike the other three, it spreads budget across all variants. Low `tau` → close to greedy; high `tau` → close to uniform.

> **Note on allocation shape:** epsilon-greedy, UCB, and Thompson sampling currently commit **100% of traffic to a single selected variant** (0% to the rest) per call. Only softmax returns a genuinely fractional split. Fractional allocation for all four is a planned change — see [ROADMAP.md](ROADMAP.md), Phase 1.

---

## API reference (`banditbrain.core`)

### Policies

Each constructor takes `metrics: list[Metric]`, plus `experiment_name: str = ""` and `date: str | None = None` (used to stamp the output; `None`/`""` means today). `get_allocation()` returns `list[Allocation]`.

```python
EpsilonGreedyBandit(metrics, epsilon=0.1, experiment_name="", date=None)
UCBBandit(metrics, c=2.0, experiment_name="", date=None)
ThompsonSamplingBandit(metrics, experiment_name="", date=None)
SoftmaxBandit(metrics, tau=0.1, experiment_name="", date=None)
```

`EpsilonGreedyBandit`, `UCBBandit`, and `ThompsonSamplingBandit` also expose `select() -> str`, which returns the chosen variant name without building `Allocation` objects.

```python
from banditbrain.core.policies import UCBBandit

bandit = UCBBandit(metrics, c=1.5, experiment_name="pricing")
winner = bandit.select()                 # -> "A"
allocation = bandit.get_allocation()     # -> [Allocation(...), ...]
```

### Models (`banditbrain.core.models`)

Pydantic models used across the engine.

- **`Metric`** — one variant's aggregated stats: `variant_name`, `clicks`, `impressions`, `total_cost`, `device`, `location`, `user_segment`, `ctr`, `ctr_se`, `ctr_ci_lower`, `ctr_ci_upper`, plus optional `cpc`/`cpv`. This is the input to every policy.
- **`Allocation`** — one variant's recommended share: `experiment_name`, `variant_name`, `allocated_pct`, `algorithm` (`"eg"`, `"ucb"`, `"ts"`, `"softmax"`), `date`. The output of every policy.
- **`Experiment`** — a raw ingested event: `experiment_name`, `variant_name`, `impressions`, `clicks`, `cost`, `event_date`, optional `context`.

### Helper (`banditbrain.core.dates`)

```python
from banditbrain.core.dates import get_prediction_date

get_prediction_date("2026-01-01")   # -> "2026-01-02"  (always +1 day)
get_prediction_date(None)           # -> tomorrow's date, ISO format
```

---

## HTTP API (`banditbrain.api`)

The FastAPI service wraps the core engine, persists to PostgreSQL, and gates everything behind JWT auth. All routes except `/signup` and `/login` require an `Authorization: Bearer <token>` header.

| Method | Path | Purpose |
|---|---|---|
| POST | `/signup` | Create an account (`email`, `password`). |
| POST | `/login` | Exchange credentials for a JWT access token. |
| POST | `/ingest` | Ingest a JSON **array** of experiment events. |
| POST | `/recommend` | Run a policy over stored metrics and persist + return allocations. |
| GET | `/experiments` | List ingested events. Filters: `experiment_name`, `date`, `limit`. |
| GET | `/metrics` | Aggregated per-variant metrics. Filters: `experiment_name`, `date`, `group_by_context`. |
| GET | `/allocations` | List persisted allocations. Filters: `experiment_name`, `date`, `algorithm`, `limit`. |
| DELETE | `/experiments` | Delete the caller's experiment records (204, no payload). |
| DELETE | `/allocations` | Delete the caller's allocation records (204, no payload). |

**`POST /recommend` body** — `method` selects the policy; only the matching param is used:

```json
{
  "experiment_name": "homepage_test",
  "method": "ts",
  "epsilon": 0.1,
  "c": 2.0,
  "tau": 0.1,
  "date": "2026-01-01"
}
```

Validation: `method` ∈ `{eg, ucb, ts, softmax}`, `epsilon` ∈ `[0, 1]`, `c`/`tau` ≥ 0. The response is a list of `Allocation` objects dated the next day. Interactive docs are served at `/docs`.

**`POST /ingest` body** — an array; `clicks` must not exceed `impressions`:

```json
[
  {
    "experiment_name": "homepage_test",
    "variant_name": "A",
    "impressions": 1000,
    "clicks": 120,
    "cost": 1.0,
    "event_date": "2026-01-01",
    "context": {"device": "mobile"}
  }
]
```

A ready-to-import request collection lives in [routes-collection/bandit-brain-routes.har](routes-collection/bandit-brain-routes.har).

### Dashboard CSV format

The Streamlit dashboard can upload real data instead of using the API. Expected columns (see [public/example_ads_data.csv](public/example_ads_data.csv)):

`variant_name, impressions, clicks, cost, device, location, user_segment, hour`

---

## Configuration

The API and dashboard read the following environment variables (see [.env.example](.env.example)):

| Variable | Used by | Description |
|---|---|---|
| `DATABASE_URL` | API | PostgreSQL connection string. |
| `HASH_SECRET_KEY` | API | Secret for signing JWTs. |
| `HASH_ALGORITHM` | API | JWT algorithm (e.g. `HS256`). |
| `HASH_TOKEN_EXPIRE_MINUTES` | API | Token lifetime in minutes. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | db | PostgreSQL bootstrap credentials. |
| `API_URL` | dashboard | Base URL the dashboard calls. |

**Policy hyperparameters** are passed per request/call, not via env:

| Param | Policy | Range | Default | Effect |
|---|---|---|---|---|
| `epsilon` | epsilon-greedy | `[0, 1]` | `0.1` | Higher → more random exploration. |
| `c` | UCB | `> 0` | `2.0` | Higher → more weight on uncertainty (more exploration). |
| `tau` | softmax | `> 0` | `0.1` | Higher → more uniform; lower → greedier. |

Database schema changes are managed with Alembic ([migrations/](migrations/)) and applied automatically when the API container starts; run them manually with `make migrate` (needs `DATABASE_URL`).

---

## Development

```bash
make install     # uv sync --all-extras
make test        # uv run pytest
make lint        # ruff check + format --check
make typecheck   # mypy on banditbrain.core
make check       # lint + typecheck + test
make seed        # load demo data into a running stack
```

Tests live in [tests/](tests/): `test_core_policies.py` (allocation correctness), `test_ingest_validation.py` (ingest rules), `test_api_smoke.py` (routes registered + auth enforced). CI runs lint → typecheck → tests on every push and PR ([.github/workflows/ci.yml](.github/workflows/ci.yml)); `pre-commit` hooks mirror it.

### Project layout

```
src/banditbrain/
  core/          # Pure bandit engine: policies + models (numpy + pydantic only)
  api/           # FastAPI layer: routes, repositories, JWT auth, validators
  simulation/    # Simulation/backtesting package (planned — currently empty)
dashboard/       # Streamlit dashboard
migrations/      # Alembic migrations
docker/          # Dockerfiles + entrypoints
scripts/         # Seed + example-data + stream generators
tests/           # pytest suite
```

The project's direction is tracked in [ROADMAP.md](ROADMAP.md).

---

## Contributing

Issues and pull requests are welcome. Please run `make check` before opening a PR so lint, types, and tests stay green.

## License

MIT — see [LICENSE](LICENSE).

---

## Open questions

A few things in the code are ambiguous; flagging rather than guessing:

1. **All-or-nothing allocation.** EG/UCB/TS return 100% to a single variant per call, and Thompson sampling is stochastic (different variant across calls on the same data). Should the README present this as the intended production behavior, or lead with it as a known limitation (as [ROADMAP.md](ROADMAP.md) Phase 1 frames it)?
2. **`select()` asymmetry.** `SoftmaxBandit` has no `select()` method while the other three do. Is that intentional, or should the API be uniform?
3. **PyPI / packaging.** Is there any intent to publish `banditbrain` to PyPI, or is source install the only supported path? The README currently assumes source-only.
