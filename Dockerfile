FROM python:3.11-slim

WORKDIR /app

# Install git (required for policyengine-us git dependency)
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./
COPY aca_calc/ ./aca_calc/
COPY src/aca_api/ ./src/aca_api/

# Install dependencies
RUN uv pip install --system -e . fastapi uvicorn[standard] pydantic

# Cloud Run uses PORT env var
ENV PORT=8080

EXPOSE 8080

# Run with uvicorn
CMD ["uvicorn", "src.aca_api.api:app", "--host", "0.0.0.0", "--port", "8080"]
