#!/bin/bash
set -e

echo "Fixing permissions..."

# Ensure directories exist (host-mounted volumes)
mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db

# Fix ownership to appuser
chown -R appuser:appuser /app/data /app/rag_bot/chroma_db

# Safe permissions
chmod -R 755 /app/data /app/rag_bot/chroma_db

echo "Dropping privileges to appuser..."

# Switch to appuser and continue
exec gosu appuser bash -c "
    if [ \"\$SKIP_CRAWL\" != \"1\" ]; then
        echo 'Starting Crawler...'
        python -m crawler.crawler

        echo 'Starting Indexer...'
        python -m rag_bot.main index
    fi

    echo 'Initializing Database...'
    python -m rag_bot.db_init

    echo 'Starting API...'
    exec uvicorn rag_bot.api:app --host 0.0.0.0 --port 8000
"
