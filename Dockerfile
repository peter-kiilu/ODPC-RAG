# syntax=docker/dockerfile:1.4
# -------------------------
# Stage 1: Builder - Build wheels for faster installs
# -------------------------
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Build all wheels at once (reuses cache if requirements.txt unchanged)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip wheel --no-deps --wheel-dir /wheels --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# -------------------------
# Stage 2: Runtime - Minimal production image
# -------------------------
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    PYTHONDONTWRITEBYTECODE=0 \
    PATH="/home/appuser/.local/bin:$PATH" \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 -m appuser

# Install runtime dependencies only (no build tools!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages from pre-built wheels
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt && \
    rm -rf /wheels requirements.txt

# Pre-download HuggingFace embedding model (saves 30-40s on first startup!)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-small-en-v1.5', cache_folder='/app/.cache')" && \
    chown -R appuser:appuser /app/.cache

# Copy application code
COPY --chown=appuser:appuser rag_bot/ ./rag_bot/
COPY --chown=appuser:appuser crawler/ ./crawler/
COPY --chown=appuser:appuser entrypoint.sh ./

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -b /app/rag_bot /app/crawler && \
    chmod +x entrypoint.sh && \
    mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db && \
    chown -R appuser:appuser /app

EXPOSE 8000

# Optimized health check with longer start period
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=2 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./entrypoint.sh"]
