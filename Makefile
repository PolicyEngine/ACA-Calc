.PHONY: install test format debug clean dev api frontend build stop

install:
	pip install -e ".[dev]"
	npm install

test:
	uv run pytest tests/ -v

format:
	black . -l 79
	@echo "Formatting complete"

debug:
	uv run streamlit run app.py

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run both frontend and backend for local development
dev:
	@echo "Starting backend (Docker) and frontend (npm)..."
	docker compose up -d
	npm run dev

# Run just the API in Docker
api:
	docker compose up

# Run just the frontend
frontend:
	npm run dev

# Build Docker image
build:
	docker build -t aca-calc-api .

# Stop Docker services
stop:
	docker compose down
