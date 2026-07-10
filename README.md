<p align="center">
  <img src="public/logo.png" alt="Logo" width="200" background="transparent"/>
</p>

# Bandit Brain

Bandit Brain is a robust experimentation and recommendation platform based on Multi-Armed Bandit (MAB) algorithms. It provides a backend REST API, dashboard for visualization, simulation scripts, and database integration for managing and analyzing experiments in real time.

---

## Demo

![Demo](public/demo.gif)

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Models](#models)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
	- [Sign up](#signup)
	- [Login](#login)
	- [Ingest Experiments](#ingest-experiments)
	- [Recommend Allocations](#recommend-allocations)
	- [List Experiments](#list-experiments)
	- [List Metrics](#list-metrics)
	- [List Allocations](#list-allocations)
	- [Delete Allocations](#delete-allocations)
	- [Delete Experiments](#delete-experiments)

- [Example Usage](#example-usage)
- [License](#license)
- [Disclaimer](#disclaimer)
- [Contributing](#contributing)

---

## Features

- REST API for experiment ingestion, recommendation, allocation, and metrics
- Dashboard for results visualization
- Upload real experiment data via CSV directly in the dashboard
- Support for multiple MAB algorithms: Epsilon-Greedy, UCB, Thompson Sampling, Softmax
- Experiment simulation and management
- Docker support for easy deployment
- PostgreSQL integration
- All dashboard visualizations use real, persisted backend data for consistency and auditability.

---

## Models

This platform supports several Multi-Armed Bandit (MAB) algorithms for experiment allocation. Below are technical details for each model, including definition, formula, recommended use cases, and tradeoffs.

### Epsilon-Greedy (EG)
**Definition:** Selects the best-known variant with probability `1 - epsilon` and explores a random variant with probability `epsilon`.

**Formula:**
- With probability `epsilon`, select a random variant.
- With probability `1 - epsilon`, select the variant with the highest observed mean reward (e.g., CTR).

**When to use:**
- When a simple balance between exploration and exploitation is needed, especially in stationary environments or when initial uncertainty is high.

**Tradeoffs:**
- Easy to implement and tune. May over-explore if `epsilon` is too high, or under-explore if too low. Does not adapt exploration rate over time.

---

### Upper Confidence Bound (UCB)
**Definition:** Selects variants based on an optimistic estimate of their performance, considering both observed mean and uncertainty.

**Formula:**
- For each variant:
  `score = mean + c * sqrt(ln(total_impressions) / impressions_variant)`
  where `c` controls exploration strength.

**When to use:**
- When it is important to prioritize less-tested variants and systematically reduce uncertainty, especially with many options.

**Tradeoffs:**
- Automatically balances exploration and exploitation. Sensitive to the choice of `c`. May over-explore rarely chosen variants.

---

### Thompson Sampling (TS)
**Definition:** Uses Bayesian inference to sample possible reward rates for each variant, balancing exploration and exploitation probabilistically.

**Formula:**
- For each variant, sample a reward rate from the Beta distribution parameterized by observed successes and failures.
- Select the variant with the highest sampled value.

**When to use:**
- Recommended for adaptive, data-scarce environments. Handles uncertainty and non-stationarity well.

**Tradeoffs:**
- Typically achieves strong empirical performance. More complex to implement and interpret. Requires probabilistic reasoning.

---

### Softmax
**Definition:** Allocates selection probabilities to each variant proportional to their observed performance, smoothed by a temperature parameter `tau`.

**Formula:**
- For each variant:
  `p_i = exp(mean_i / tau) / sum_j exp(mean_j / tau)`
  where `tau` controls the degree of exploration.

**When to use:**
- Useful when all variants should have a nonzero chance of selection, even if their performance is low. Good for continuous exploration.

**Tradeoffs:**
- Sensitive to `tau`: low values favor exploitation, high values favor exploration. May require careful tuning for optimal results.

---

## Project Structure

```
src/banditbrain/
  core/          # Pure bandit engine: policies, domain models (no API/DB dependencies)
  api/           # FastAPI layer: routes, repositories, auth, validation
  simulation/    # Simulation & backtesting framework (in progress)
dashboard/       # Streamlit dashboard
migrations/      # Alembic database migrations
docker/          # Dockerfiles and entrypoints
scripts/         # Seed script, data stream generator
tests/           # Test suite (pytest)
public/          # Assets and example data
routes-collection/
```

---

## Getting Started

### Local Setup

1. Clone the repository:
	 ```bash
	 git clone https://github.com/tzpereira/bandit-brain.git
	 cd bandit-brain
	 cp .env.example .env
	 ```

2. Quick start (full stack):
	```bash
	docker compose up --build
	```

3. Seed demo data (optional, with the stack running):
	```bash
	make seed
	```

### Development

Dependencies are managed with [uv](https://docs.astral.sh/uv/):

```bash
make install     # uv sync --all-extras
make test        # pytest
make lint        # ruff check + format check
make typecheck   # mypy on the core package
make check       # all of the above
```

Database migrations use Alembic and run automatically when the API container starts. To run them manually: `make migrate` (requires `DATABASE_URL`).

---

## Using the Dashboard with CSV Uploads

The dashboard allows you to either simulate experiment data or upload your own real data using a CSV file. This makes it easy to analyze and visualize results from actual experiments, not just synthetic ones.

**How to use:**

1. Open the dashboard in your browser.
2. Select **Upload CSV** as the data input mode.
3. Upload your CSV file containing experiment data.
4. The dashboard will process your data and display all visualizations and metrics based on your uploaded file.

**Expected CSV format:**

| variant_name | impressions | clicks | cost | device | location | user_segment  | hour |
|--------------|-------------|--------|------|--------|----------|---------------|------|
| A            | 1000        | 120    | 1.0  | mobile | BRA      | new_user      | 14   |
| B            | 950         | 110    | 0.9  | desktop| USA      | returning_user| 15   |

You can download a CSV template directly from the dashboard interface.

**Tip:** All columns are required for best results. The dashboard will use your data for all visualizations, metrics, and recommendations.

### Docker

1. Make sure Docker and Docker Compose are installed.
2. Run:
	 ```bash
	 docker-compose up --build
	 ```
3. Backend and dashboard will be available at the configured ports (see `docker-compose.yaml`).

---

## Authentication & JWT Usage

All API usage requires user authentication. You must create an account and use a JWT token for all protected routes.

**How to authenticate:**

1. Create an account using `/signup`.
2. Log in using `/login` to receive a JWT token.
3. For all protected routes, include the JWT token in the `Authorization` header as:
	 ```
	 Authorization: Bearer <your-jwt-token>
	 ```

**Note:** If the JWT token is missing or invalid, requests to protected endpoints will be rejected.

---

## API Documentation
### Signup

**POST /signup**

Create a new user account.

**Payload Example:**
```json
{
	"email": "user@example.com",
	"password": "yourpassword"
}
```

**Response Example:**
```json
{
	"user_id": 1,
	"email": "user@example.com"
}
```

---

### Login

**POST /login**

Authenticate an existing user and receive a JWT token.

**Payload Example:**
```json
{
	"email": "user@example.com",
	"password": "yourpassword"
}
```

**Response Example:**
```json
{
	"access_token": "<jwt-token>",
	"token_type": "bearer"
}
```

---

> **All routes below require the JWT token in the Authorization header.**
### Ingest Experiments

**POST /ingest**

Ingest one or more experiment events. Accepts a JSON array of experiment objects.

**Payload Example:**
```json
[
	{
		"experiment_name": "homepage_test",
		"variant_name": "A",
		"impressions": 1000,
		"clicks": 120,
		"cost": 1.0,
		"event_date": "2025-08-24",
		"context": {"device": "mobile"}
	}
]
```

**Response:**
```json
{ "status": "success" }
```

---

### Recommend Allocations

**POST /recommend**

Get recommended allocation for experiment variants using a chosen algorithm.

**Payload Example:**
```json
{
	"experiment_name": "homepage_test",
	"method": "eg",        // "eg", "ucb", "ts", "softmax"
	"epsilon": 0.1,        // for "eg"
	"c": 2.0,              // for "ucb"
	"tau": 0.1,            // for "softmax"
	"date": "2025-08-24"  // ISO format (YYYY-MM-DD)
}
```

**Response Example:**
```json
[
	{
		"id": null,
		"experiment_name": "homepage_test",
		"variant_name": "A",
		"allocated_pct": 1.0,
		"algorithm": "eg",
		"date": "2025-08-25", // always predicts for the next day (allocation date is always the day after the input date)
		"created_at": null
	},
	{
		"id": null,
		"experiment_name": "homepage_test",
		"variant_name": "B",
		"allocated_pct": 0.0,
		"algorithm": "eg",
		"date": "2025-08-25", // always predicts for the next day
		"created_at": null
	}
]
```

**Note:** The `date` field in the response always refers to the next day after the input date, representing a forecast for future allocation.

---

### List Experiments

**GET /experiments**

Retrieve a list of experiments, optionally filtered by experiment name, date, or limited in number.

**Query Parameters:**

| Name             | Type   | Required | Description                                 |
|------------------|--------|----------|---------------------------------------------|
| experiment_name  | string | No       | Filter by experiment name                   |
| date             | string | No       | Filter by event date (YYYY-MM-DD)           |
| limit            | int    | No       | Limit the number of returned experiments    |

**Example Request:**
```
GET /experiments?experiment_name=homepage_test&date=2025-08-24&limit=10
```

**Response:**
Returns a JSON array of experiment objects.

**Response Example:**
```json
[
	{
		"id": 1,
		"experiment_name": "homepage_test",
		"variant_name": "A",
		"impressions": 1000,
		"clicks": 120,
		"cost": 1.0,
		"event_date": "2025-08-24",
		"context": {"device": "mobile"},
		"created_at": "2025-08-24T12:00:00"
	},
	{
		"id": 2,
		"experiment_name": "homepage_test",
		"variant_name": "B",
		"impressions": 950,
		"clicks": 110,
		"cost": 0.9,
		"event_date": "2025-08-24",
		"context": {"device": "desktop"},
		"created_at": "2025-08-24T12:00:00"
	}
]
```

**What it does:**
Returns all experiments matching the filters, including all fields for each experiment.

---

### List Metrics

**GET /metrics**

Retrieve aggregated metrics (impressions, clicks, CTR, etc.) for each variant, with optional filters and grouping.

**Query Parameters:**

| Name              | Type    | Required | Description                                 |
|-------------------|---------|----------|---------------------------------------------|
| experiment_name   | string  | No       | Filter by experiment name                   |
| date              | string  | No       | Filter by event date (YYYY-MM-DD)           |
| group_by_context  | boolean | No       | Group metrics by context fields             |

**Example Request:**
```
GET /metrics?experiment_name=homepage_test&date=2025-08-24&group_by_context=true
```

**Response:**
Returns a JSON array of metric objects.

**Response Example:**
```json
[
	{
		"variant_name": "A",
		"clicks": 120,
		"total_cost": 1.0,
		"impressions": 1000,
		"device": "mobile",
		"location": "BR",
		"user_segment": "new",
		"cpc": 0.0083,
		"cpv": 0.008,
		"ctr": 0.12,
		"ctr_se": 0.01,
		"ctr_ci_lower": 0.10,
		"ctr_ci_upper": 0.14
	},
	{
		"variant_name": "B",
		"clicks": 110,
		"total_cost": 0.9,
		"impressions": 950,
		"device": "desktop",
		"location": "BR",
		"user_segment": "returning",
		"cpc": 0.0081,
		"cpv": 0.0079,
		"ctr": 0.115,
		"ctr_se": 0.009,
		"ctr_ci_lower": 0.097,
		"ctr_ci_upper": 0.133
	}
]
```

**What it does:**
Returns aggregated metrics for each variant, optionally grouped by context fields, useful for performance analysis and reporting.

### List Allocations

**GET /allocations**

Retrieve persisted allocation results for experiment variants. This endpoint returns the allocation data generated and stored by the /recommend route.

**Query Parameters:**

| Name             | Type   | Required | Description                                 |
|------------------|--------|----------|---------------------------------------------|
| experiment_name  | string | No       | Filter by experiment name                   |
| date             | string | No       | Filter by allocation date (YYYY-MM-DD, ISO format)      |
| algorithm        | string | No       | Filter by algorithm used (eg, ucb, ts, softmax) |
| limit            | int    | No       | Limit the number of returned allocations    |

**Example Request:**
```
GET /allocations?experiment_name=homepage_test&date=2025-08-24&algorithm=eg&limit=10
```

**Response:**
Returns a JSON array of allocation objects.

**Response Example:**
```json
[
	{
		"id": 1,
		"experiment_name": "homepage_test",
		"variant_name": "A",
		"allocated_pct": 1.0,
		"algorithm": "eg",
		"date": "2025-08-25", // always predicts for the next day
		"created_at": "2025-08-24T12:00:00"
	},
	{
		"id": 2,
		"experiment_name": "homepage_test",
		"variant_name": "B",
		"allocated_pct": 0.0,
		"algorithm": "eg",
		"date": "2025-08-25", // always predicts for the next day
		"created_at": "2025-08-24T12:00:00"
	}
]
```

**Note:** The `date` field in the response always refers to the next day after the input date, representing a forecast for future allocation. All date fields must use ISO format (`YYYY-MM-DD`).

---

### Delete Allocations

**DELETE /delete/allocations**

Delete allocation records for a given experiment or variant.

- No payload required.
- No response body returned on success (HTTP 204).

---

### Delete Experiments

**DELETE /delete/experiments**

Delete experiment records by experiment name.

- No payload required.
- No response body returned on success (HTTP 204).

---

## Example Usage

- See example routes in `routes-collection/bandit-brain-routes.har`

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Disclaimer

This software is provided for educational and research purposes only. It is not intended for commercial use. Use at your own risk.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
