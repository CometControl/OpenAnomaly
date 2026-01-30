# Multi-stage build for OpenAnomaly
# 1. Builder Stage: Install dependencies with UV
FROM python:3.14-slim AS builder

WORKDIR /app

# Install system dependencies (git)
# git removed

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy source code (needed for local package install)
COPY openanomaly ./openanomaly
COPY tests ./tests
COPY manage.py ./

# Install dependencies (sync utilizes the lockfile for deterministic builds)
# We use --frozen to ensure we don't modify the lockfile during build
ARG INSTALL_ML=false
RUN if [ "$INSTALL_ML" = "true" ]; then \
        uv sync --locked --no-dev --extra ml; \
    else \
        uv sync --locked --no-dev; \
    fi

# 2. Runtime Stage: Minimal image
FROM python:3.14-slim

WORKDIR /app

# Install uv (needed for local dev with uv sync)
RUN pip install uv

# Install runtime dependencies (e.g. libgomp for some ML libraries if needed)
# RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user for security (optional but recommended for prod)
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser

# Default command (can be overridden by Compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
