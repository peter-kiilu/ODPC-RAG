# syntax=docker/dockerfile:1.4
# -------------------------
# Stage 1: Builder - Install dependencies
# -------------------------
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install all packages with pip cache mount (fastest approach)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Pre-download HuggingFace embedding model into cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# -------------------------
# Stage 2: Runtime - Minimal production image
# -------------------------
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    PATH="/home/appuser/.local/bin:$PATH"

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

# Copy Python packages from builder (system site-packages)
COPY --from=builder /usr/local /usr/local

# Copy HuggingFace cache from builder
COPY --from=builder /root/.cache/huggingface /app/.cache/huggingface

# Copy application code
COPY --chown=appuser:appuser rag_bot/ ./rag_bot/
COPY --chown=appuser:appuser crawler/ ./crawler/
COPY --chown=appuser:appuser entrypoint.sh ./

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -b /app/rag_bot /app/crawler 2>/dev/null || true

# Setup directories and permissions
RUN chmod +x entrypoint.sh && \
    mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db /app/.cache/huggingface && \
    chown -R appuser:appuser /app

EXPOSE 8000

# Optimized health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=2 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./entrypoint.sh"]
