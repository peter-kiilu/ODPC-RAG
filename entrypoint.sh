#!/bin/bash
set -e

# -------------------------
# Directories & Permissions
# -------------------------
mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db
chown -R appuser:appuser /app/data /app/rag_bot/chroma_db
chmod -R 755 /app/data /app/rag_bot/chroma_db

# -------------------------
# Optionally skip crawling/indexing
# -------------------------
if [ "$SKIP_CRAWL" != "1" ]; then
    echo "Starting Crawler..."
    python -m crawler.crawler

    echo "Starting Indexer..."
    python -m rag_bot.main index
fi

# -------------------------
# Database initialization
# -------------------------
echo "Initializing Database..."
python -m rag_bot.db_init

# -------------------------
# Start API
# -------------------------
echo "Starting API..."
exec uvicorn rag_bot.api:app --host 0.0.0.0 --port 8000
