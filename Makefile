.PHONY: help install lint format test test-unit test-e2e docker-up docker-down clean cli query

help:
	@echo "Available commands:"
	@echo "  make cli          - Launch interactive GraphMind terminal CLI shell"
	@echo "  make query Q=...  - Run a one-shot grounded query via CLI"
	@echo "  make install      - Install python dependencies in editable mode with dev extras"
	@echo "  make lint         - Run ruff lint on backend"
	@echo "  make format       - Format backend code with ruff"
	@echo "  make test         - Run all unit and integration tests"
	@echo "  make test-e2e     - Run end-to-end pipeline verification"
	@echo "  make docker-up    - Build and launch all services with docker-compose"
	@echo "  make docker-down  - Stop all running docker containers"
	@echo "  make clean        - Remove caches and temporary files"

cli:
	python -m kgrag.cli interactive

query:
	python -m kgrag.cli query "$(Q)"

install:
	pip install --upgrade pip
	pip install -e ".[dev]"
	cd frontend && npm install

lint:
	ruff check .
	ruff format --check .
	cd frontend && npm run lint

format:
	ruff check --fix .
	ruff format .

test:
	pytest tests/unit tests/integration -v

test-unit:
	pytest tests/unit -v

test-e2e:
	python test_e2e.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf dist build *.egg-info frontend/dist
