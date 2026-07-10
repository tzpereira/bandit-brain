.PHONY: install up down test lint format typecheck check seed migrate

install:
	uv sync --all-extras

up:
	docker compose up --build -d

down:
	docker compose down

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy

check: lint typecheck test

seed:
	uv run python scripts/seed.py

migrate:
	uv run alembic upgrade head
