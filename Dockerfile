FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
RUN npm run build

FROM pytorch/pytorch:2.1.0-cpu AS backend-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

WORKDIR /app

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 -m appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /root/.local /home/appuser/.local

COPY --chown=appuser:appuser rag_bot/ ./rag_bot/
COPY --chown=appuser:appuser crawler/ ./crawler/

COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html

RUN mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db \
    && chown -R appuser:appuser /app

COPY docker/nginx.conf /etc/nginx/sites-available/default

COPY docker/supervisor.conf /etc/supervisor/conf.d/app.conf

RUN mkdir -p /var/log/supervisor

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/app.conf"]
