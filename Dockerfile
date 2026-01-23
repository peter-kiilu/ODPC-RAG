# syntax=docker/dockerfile:1.4
# -------------------------
# Stage 1: Builder
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
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-deps --wheel-dir /wheels -r requirements.txt

# -------------------------
# Stage 2: Runtime
# -------------------------
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    PATH="/home/appuser/.local/bin:$PATH" \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    CUDA_VISIBLE_DEVICES=""

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 -m appuser

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python packages from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && \
    rm -rf /wheels

# Pre-download HuggingFace embedding model (saves 30-40 sec on startup)
RUN --mount=type=cache,target=/root/.cache/huggingface \
    python -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('BAAI/bge-small-en-v1.5', cache_folder='/tmp/hf'); \
    import shutil; \
    shutil.copytree('/tmp/hf', '/app/.cache/huggingface', dirs_exist_ok=True)" && \
    chown -R appuser:appuser /app/.cache

# Copy application code
COPY --chown=appuser:appuser rag_bot/ ./rag_bot/
COPY --chown=appuser:appuser crawler/ ./crawler/
COPY --chown=appuser:appuser entrypoint.sh ./

# Compile Python bytecode for faster startup
RUN python -m compileall -b /app/rag_bot /app/crawler

# Setup directories and permissions
RUN chmod +x entrypoint.sh && \
    mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Optimized healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=2 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
