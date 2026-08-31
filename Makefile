.PHONY: up down test lint fmt migrate

up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check . && uv run mypy app

fmt:
	cd backend && uv run black .

migrate:
	cd backend && uv run alembic upgrade head
