# Contributing to Bandit Brain

Issues and pull requests are welcome. This is a portfolio project, so the bar
is "correct and checkable" rather than "enterprise-hardened" — see
[ROADMAP.md](ROADMAP.md) for what's intentionally in and out of scope.

## Getting set up

```bash
git clone https://github.com/tzpereira/bandit-brain.git
cd bandit-brain
make install     # uv sync --all-extras
```

Core engine work (`src/banditbrain/core/`, `src/banditbrain/simulation/`)
needs nothing beyond that. To run the full stack (API + dashboard +
Postgres):

```bash
cp .env.example .env
make up          # docker compose up --build -d
make seed        # optional: load demo data
```

## Before opening a PR

```bash
make check       # ruff check + ruff format --check + mypy (core/) + pytest
```

`pre-commit` mirrors this locally on every commit:

```bash
uv run pre-commit install
```

CI runs the same checks on every push/PR ([.github/workflows/ci.yml](.github/workflows/ci.yml)).

## What a good PR looks like

- **Tests first-class.** New behavior in `core/` or `simulation/` needs unit
  tests; a bug fix needs a test that would have caught it. See the
  [Development](README.md#development) section of the README for where
  existing tests live.
- **`core/` stays pure.** No FastAPI, no database, no Streamlit imports in
  `src/banditbrain/core/` — it should stay importable and testable with only
  `numpy` + `pydantic`. `mypy` is scoped to this package for the same reason.
- **Reproducible claims.** If you're adding a number to the README's Results
  section, it needs to come from `make report` / `make figures`, with the
  scenario/seed documented — not hand-computed or eyeballed.
- **Scope discipline.** Check the [Non-goals](ROADMAP.md#non-goals) section
  before adding a feature; a lot of plausible-looking additions (real-time
  streaming, drift detection, budget-aware allocation) are deliberately out
  of scope so the core thesis stays sharp.

## Reporting bugs / proposing features

Open a GitHub issue. For bugs, include: what you ran, what you expected,
what happened instead, and (if it's a policy/estimator question) the
metrics/seed that reproduce it.

## Security

This project has no formal security disclosure process (it's a portfolio
project, not a production service). If you find something concerning, open
an issue — please don't include real credentials or PII in the report.
