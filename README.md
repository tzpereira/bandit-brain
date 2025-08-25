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
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
	- [Ingest Experiments](#ingest-experiments)
	- [Recommend Allocations](#recommend-allocations)
	- [List Experiments](#list-experiments)
	- [List Metrics](#list-metrics)
	- [List Allocations](#list-allocations)
	- [Delete Allocations](#delete-allocations)
	- [Delete Experiments](#delete-experiments)
    
- [Models](#models)
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

## Project Structure

```
backend/
  app/
    repositories/
    routes/
    services/
    validators/
  Dockerfile
  requirements.txt
dashboard/
  Dockerfile
  requirements.txt
db/
routes-collection/
scripts/
public/
```

---

## Getting Started

### Local Setup

1. Clone the repository:
	 ```bash
	 git clone https://github.com/tzpereira/bandit-brain.git
	 cd bandit-brain
	 ```

2. Quick start:
	```bash
	docker-compose up --build
	```

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

## API Documentation
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
