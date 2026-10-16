# Multi-stage production Dockerfile for Knowledge Graph RAG API
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the application and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final runtime image
FROM python:3.12-slim-bookworm AS runner

# Install runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -g 10001 kgrag && \
    useradd -u 10001 -g kgrag -s /bin/bash -m kgrag

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=kgrag:kgrag /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application configuration and source code
COPY --chown=kgrag:kgrag config/ ./config/
COPY --chown=kgrag:kgrag src/ ./src/

USER kgrag

EXPOSE 8000

# Health check against FastAPI health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch production ASGI server
CMD ["uvicorn", "kgrag.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
