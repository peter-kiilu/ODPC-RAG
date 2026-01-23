#!/bin/bash
set -e

echo "======================================"
echo "ODPC Kenya RAG Bot - Starting..."
echo "======================================"

# Ensure directories exist (host-mounted volumes)
mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db

# Fix ownership to appuser
chown -R appuser:appuser /app/data /app/rag_bot/chroma_db 2>/dev/null || true
chmod -R 755 /app/data /app/rag_bot/chroma_db 2>/dev/null || true

echo "Switching to non-root user..."

# Switch to appuser and continue
exec gosu appuser bash -c '
    # Parse SKIP_CRAWL (accepts: true, 1, yes, skip)
    SHOULD_SKIP=false
    if [[ "$SKIP_CRAWL" =~ ^(true|1|yes|skip)$ ]]; then
        SHOULD_SKIP=true
    fi

    # Pre-download HuggingFace model on first run (if not in volume cache)
    if [ ! -f /app/.cache/huggingface/.model_downloaded ]; then
        echo "📥 Downloading embedding model (first time only, ~133MB)..."
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer(\"BAAI/bge-small-en-v1.5\")" || echo "⚠️  Model download will happen during API startup"
        touch /app/.cache/huggingface/.model_downloaded 2>/dev/null || true
        echo "✅ Model cached for future runs"
    else
        echo "✅ Using cached embedding model"
    fi

    if [ "$SHOULD_SKIP" = "false" ]; then
        echo "📥 Starting Crawler..."
        python -m crawler.crawler || echo "⚠️  Crawler failed, continuing..."

        echo "📚 Starting Indexer..."
        python -m rag_bot.main index || echo "⚠️  Indexer failed, continuing..."
    else
        echo "⏭️  Skipping crawler and indexer (SKIP_CRAWL=$SKIP_CRAWL)"
    fi

    # Initialize database (skip if already done)
    if [ ! -f /app/data/.db_initialized ]; then
        echo "🗄️  Initializing Database..."
        python -m rag_bot.db_init
        touch /app/data/.db_initialized
        echo "✅ Database initialized"
    else
        echo "✅ Database already initialized, skipping..."
    fi

    echo "🚀 Starting API..."
    exec uvicorn rag_bot.api:app --host 0.0.0.0 --port 8000 --workers 1
'
