#!/bin/bash
set -e

# Ensure directories exist (in case volume mount hid them or they are empty)
mkdir -p /app/data/markdown /app/data/documents /app/rag_bot/chroma_db

echo "Starting Crawler..."
python -m crawler.crawler

echo "Starting Indexer..."
python -m rag_bot.main index

echo "Initializing Database..."
python -m rag_bot.db_init

echo "Starting API..."
exec uvicorn rag_bot.api:app --host 0.0.0.0 --port 8000
