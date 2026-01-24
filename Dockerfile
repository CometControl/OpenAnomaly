# Multi-stage build for OpenAnomaly
# 1. Builder Stage: Install dependencies with UV
FROM python:3.14-slim AS builder

WORKDIR /app

# Install system dependencies (git)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
# COPY uv.lock . # Uncomment if lock file exists and is stable

# Create virtual environment and install dependencies
# We install into a virtual environment that we can copy over
ENV VIRTUAL_ENV=/app/.venv
RUN uv venv $VIRTUAL_ENV --python /usr/local/bin/python
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies
ARG INSTALL_ML=false
RUN if [ "$INSTALL_ML" = "true" ]; then \
        uv pip install --python $VIRTUAL_ENV -e ".[ml]"; \
    else \
        uv pip install --python $VIRTUAL_ENV -e .; \
    fi

# 2. Runtime Stage: Minimal image
FROM python:3.14-slim

WORKDIR /app

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
