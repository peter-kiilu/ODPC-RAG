# -------------------------
# Stage 1: Builder
# -------------------------
FROM python:3.11-slim AS backend-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /app

# Build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install PyTorch CPU-only
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# -------------------------
# Stage 2: Final Image
# -------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/venv/bin:$PATH"

WORKDIR /app

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 -m appuser

# Copy virtual environment (will be owned by root initially)
COPY --from=backend-builder /app/venv /app/venv

# Copy project files
COPY rag_bot/ ./rag_bot/
COPY crawler/ ./crawler/
COPY entrypoint.sh ./

# Create directories and fix ALL permissions in ONE layer
# This is the key: doing it all at once is much faster than multiple chown operations
RUN chmod +x entrypoint.sh && \
    mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db /app/.cache/huggingface && \
    chown -R appuser:appuser /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./entrypoint.sh"]