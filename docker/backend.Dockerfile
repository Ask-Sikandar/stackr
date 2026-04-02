FROM python:3.12-slim

# System dependencies for psycopg binary and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
# README.md must accompany pyproject.toml — hatchling reads it at build time
COPY pyproject.toml README.md ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy project
COPY . .

# Pre-download the embedding model so container startup is fast
RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000

CMD ["uv", "run", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
