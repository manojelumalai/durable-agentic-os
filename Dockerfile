FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for ultra-fast dependency management
COPY --from=ghcr.io/astral-sh/uv:0.5.1 /uv /bin/uv

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN uv pip install --system --no-cache -e .

EXPOSE 8000

CMD ["uvicorn", "durable_agent.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
